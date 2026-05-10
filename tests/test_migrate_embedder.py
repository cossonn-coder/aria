"""
tests/test_migrate_embedder.py — ARIA Sprint 6 · T-Embedder2 D
===============================================================
Tests unitaires des fonctions pures et défensives de migrate_embedder.py.

Périmètre explicitement exclu :
- ChromaDB (aucun import, aucune collection réelle)
- sentence-transformers (aucun téléchargement HuggingFace)
- Intégration ChromaDB complète → couverte par Claude Code en T-Embedder3

Lancer avec :
    pytest tests/test_migrate_embedder.py -v
"""

import logging
import os
import sys
import tarfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import des fonctions sous test
# On importe depuis le module en supposant que le projet est à la racine
# et que pytest est lancé depuis là (ou que conftest.py ajoute aria/ au path).
# ---------------------------------------------------------------------------
from scripts.migrate_embedder import (
    MODEL_EXPECTED_DIM,
    _expected_dim,
    _resolve_palace,
    _sha256,
    etape_c_check_marker,
    etape_c_write_marker,
    rollback_depuis_snapshot,
)


# ===========================================================================
# 1. test_sha256_deterministic
# ===========================================================================

class TestSha256:
    def test_same_input_same_output(self):
        """_sha256 est déterministe : même entrée → même hash."""
        model = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        assert _sha256(model) == _sha256(model)

    def test_different_input_different_output(self):
        """Deux entrées proches produisent des hashes distincts."""
        h1 = _sha256("all-MiniLM-L6-v2")
        h2 = _sha256("all-MiniLM-L6-v3")  # une seule lettre de différence
        assert h1 != h2

    def test_output_is_64_hex_chars(self):
        """SHA-256 produit exactement 64 caractères hexadécimaux."""
        h = _sha256("aria")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_empty_string_is_stable(self):
        """Le hash d'une chaîne vide est stable (valeur de référence connue)."""
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert _sha256("") == expected


# ===========================================================================
# 2. test_resolve_palace_expanduser
# ===========================================================================

class TestResolvePalace:
    def test_tilde_is_expanded(self, monkeypatch, tmp_path):
        """
        _resolve_palace doit étendre le ~ vers le répertoire home.
        On force HOME à tmp_path pour que le test soit hermétique.
        """
        monkeypatch.setenv("HOME", str(tmp_path))
        # Après l'appel, ~ doit avoir été remplacé par tmp_path
        result = _resolve_palace("~/.mempalace/palace")
        assert not result.parts[0] == "~", "Le ~ n'a pas été résolu"
        assert str(tmp_path) in str(result)

    def test_absolute_path_unchanged(self, tmp_path):
        """Un chemin absolu est retourné résolu sans modification."""
        palace = tmp_path / "palace"
        result = _resolve_palace(str(palace))
        assert result == palace.resolve()

    def test_returns_path_object(self, tmp_path):
        """Le retour est toujours un objet Path."""
        result = _resolve_palace(str(tmp_path))
        assert isinstance(result, Path)


# ===========================================================================
# 3. test_expected_dim_known_models
# ===========================================================================

class TestExpectedDim:
    @pytest.mark.parametrize("model_name,expected", list(MODEL_EXPECTED_DIM.items()))
    def test_all_known_models(self, model_name, expected):
        """_expected_dim retourne la bonne valeur pour chaque modèle du registre."""
        assert _expected_dim(model_name) == expected

    def test_minilm_without_prefix(self):
        """all-MiniLM-L6-v2 sans préfixe sentence-transformers/ → 384."""
        assert _expected_dim("all-MiniLM-L6-v2") == 384

    def test_minilm_with_prefix(self):
        """sentence-transformers/all-MiniLM-L6-v2 → 384."""
        assert _expected_dim("sentence-transformers/all-MiniLM-L6-v2") == 384

    def test_mpnet_without_prefix(self):
        """paraphrase-multilingual-mpnet-base-v2 sans préfixe → 768."""
        assert _expected_dim("paraphrase-multilingual-mpnet-base-v2") == 768

    def test_mpnet_with_prefix(self):
        """sentence-transformers/paraphrase-multilingual-mpnet-base-v2 → 768."""
        assert _expected_dim(
            "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        ) == 768

    def test_prefix_fallback_symmetry(self):
        """
        Qu'on passe le nom avec ou sans préfixe sentence-transformers/,
        le résultat est identique pour les modèles connus des deux formes.
        """
        pairs = [
            ("all-MiniLM-L6-v2", "sentence-transformers/all-MiniLM-L6-v2"),
            (
                "paraphrase-multilingual-mpnet-base-v2",
                "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
            ),
        ]
        for short, full in pairs:
            assert _expected_dim(short) == _expected_dim(full), (
                f"Asymétrie de résolution entre '{short}' et '{full}'"
            )


# ===========================================================================
# 4. test_expected_dim_unknown_raises
# ===========================================================================

class TestExpectedDimUnknown:
    def test_unknown_model_raises_value_error(self):
        """Un modèle inconnu lève ValueError."""
        with pytest.raises(ValueError):
            _expected_dim("bert-base-uncased")

    def test_error_message_mentions_registre_local(self):
        """Le message d'erreur mentionne 'registre local'."""
        with pytest.raises(ValueError, match="registre local"):
            _expected_dim("unknown-model-xyz")

    def test_error_message_lists_known_models(self):
        """
        Le message d'erreur liste au moins un modèle connu du registre,
        pour aider au diagnostic.
        """
        with pytest.raises(ValueError) as exc_info:
            _expected_dim("mon-modele-imaginaire")
        error_text = str(exc_info.value)
        # Au moins un des modèles connus doit apparaître dans le message
        known = list(MODEL_EXPECTED_DIM.keys())
        assert any(m in error_text for m in known), (
            f"Aucun modèle connu trouvé dans le message d'erreur : {error_text!r}"
        )

    def test_empty_string_raises(self):
        """Une chaîne vide lève ValueError sans planter."""
        with pytest.raises(ValueError):
            _expected_dim("")


# ===========================================================================
# 5. test_marker_idempotence
# ===========================================================================

class TestMarkerIdempotence:
    def test_detects_already_migrated_and_exits_0(self, tmp_path):
        """
        Si le marker contient le hash du modèle cible, etape_c_check_marker
        appelle sys.exit(0) — refus propre, pas une erreur.
        """
        to_model = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

        # Écrire le marker en mode non-dry-run
        etape_c_write_marker(tmp_path, to_model, dry_run=False)
        assert (tmp_path / ".embedder-migration-marker").exists()

        # Relancer check_marker → doit sys.exit(0)
        with pytest.raises(SystemExit) as exc_info:
            etape_c_check_marker(tmp_path, to_model, dry_run=False)

        assert exc_info.value.code == 0, (
            f"Attendu exit code 0 (refus propre), obtenu : {exc_info.value.code}"
        )

    def test_write_marker_creates_file(self, tmp_path):
        """etape_c_write_marker crée bien le fichier marker."""
        to_model = "all-MiniLM-L6-v2"
        etape_c_write_marker(tmp_path, to_model, dry_run=False)
        marker_path = tmp_path / ".embedder-migration-marker"
        assert marker_path.exists()
        assert len(marker_path.read_text(encoding="utf-8").strip()) == 64  # SHA-256

    def test_write_marker_noop_in_dry_run(self, tmp_path):
        """En dry-run, le marker n'est pas créé."""
        etape_c_write_marker(tmp_path, "all-MiniLM-L6-v2", dry_run=True)
        assert not (tmp_path / ".embedder-migration-marker").exists()

    def test_marker_content_is_hash_of_model(self, tmp_path):
        """Le contenu du marker est exactement le SHA-256 du nom du modèle."""
        to_model = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        etape_c_write_marker(tmp_path, to_model, dry_run=False)
        content = (tmp_path / ".embedder-migration-marker").read_text().strip()
        assert content == _sha256(to_model)


# ===========================================================================
# 6. test_marker_different_model_continues
# ===========================================================================

class TestMarkerDifferentModel:
    def test_different_hash_logs_continue(self, tmp_path, caplog):
        """
        Marker présent avec un hash différent (migration vers un autre modèle) :
        la fonction logge qu'on continue et NE fait PAS sys.exit.
        """
        # Écrire un marker pour le modèle source
        etape_c_write_marker(tmp_path, "all-MiniLM-L6-v2", dry_run=False)

        # Lancer check_marker pour un modèle différent → doit continuer sans exit
        to_model = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        with caplog.at_level(logging.INFO, logger="aria.migrate_embedder"):
            # Ne doit PAS lever SystemExit
            etape_c_check_marker(tmp_path, to_model, dry_run=False)

        # Vérifier qu'un message de "on continue" est logué
        messages = " ".join(caplog.messages)
        assert "continue" in messages.lower() or "nouveau modèle" in messages.lower(), (
            f"Message de continuation attendu dans les logs. Logs capturés : {caplog.messages}"
        )

    def test_no_marker_logs_first_migration(self, tmp_path, caplog):
        """Sans marker, la fonction logge qu'il s'agit d'une première migration."""
        to_model = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        with caplog.at_level(logging.INFO, logger="aria.migrate_embedder"):
            etape_c_check_marker(tmp_path, to_model, dry_run=False)

        messages = " ".join(caplog.messages)
        assert "première migration" in messages.lower() or "aucun marker" in messages.lower(), (
            f"Message 'première migration' attendu. Logs : {caplog.messages}"
        )


# ===========================================================================
# 7. test_rollback_no_snapshot_logs_warning
# ===========================================================================

class TestRollbackNoSnapshot:
    def test_none_snapshot_logs_restauration_manuelle(self, tmp_path, caplog):
        """
        rollback_depuis_snapshot avec snapshot_path=None doit loguer
        'restauration manuelle requise' sans lever d'exception.
        """
        palace_path = tmp_path / "palace"
        palace_path.mkdir()

        with caplog.at_level(logging.ERROR, logger="aria.migrate_embedder"):
            # Ne doit pas lever d'exception
            rollback_depuis_snapshot(palace_path, snapshot_path=None)

        messages = " ".join(caplog.messages).lower()
        assert "restauration manuelle" in messages, (
            f"'restauration manuelle requise' attendu dans les logs. Logs : {caplog.messages}"
        )

    def test_none_snapshot_does_not_raise(self, tmp_path):
        """Appel avec snapshot_path=None ne plante pas, même si palace existe."""
        palace_path = tmp_path / "palace"
        palace_path.mkdir()
        # Doit terminer sans exception
        rollback_depuis_snapshot(palace_path, snapshot_path=None)


# ===========================================================================
# 8. test_rollback_restores_from_tarball
# ===========================================================================

class TestRollbackRestoreFromTarball:
    def _create_palace(self, base: Path) -> Path:
        """Crée un répertoire palace factice avec quelques fichiers."""
        palace = base / "palace"
        palace.mkdir()
        (palace / "chroma.sqlite3").write_text("données factices sqlite", encoding="utf-8")
        sub = palace / "sub"
        sub.mkdir()
        (sub / "data.bin").write_bytes(b"\x00\x01\x02\x03")
        return palace

    def _make_tarball(self, palace: Path, dest: Path) -> Path:
        """Crée un tar.gz du répertoire palace dans dest."""
        snapshot = dest / "snapshot.tar.gz"
        with tarfile.open(snapshot, "w:gz") as tar:
            tar.add(palace, arcname=palace.name)
        return snapshot

    def test_files_restored_after_corruption(self, tmp_path):
        """
        Scénario : palace existant → snapshot → palace vidé (corruption) →
        rollback → fichiers d'origine restaurés.
        """
        palace = self._create_palace(tmp_path)
        snapshot = self._make_tarball(palace, tmp_path)

        # Simuler une corruption : vider le répertoire palace
        import shutil
        shutil.rmtree(palace)
        assert not palace.exists(), "Le palace devrait être absent avant rollback"

        # Rollback
        rollback_depuis_snapshot(palace, snapshot)

        # Vérifications
        assert palace.exists(), "Le palace devrait être restauré"
        assert (palace / "chroma.sqlite3").exists(), "chroma.sqlite3 absent après rollback"
        assert (palace / "sub" / "data.bin").exists(), "sub/data.bin absent après rollback"

        content = (palace / "chroma.sqlite3").read_text(encoding="utf-8")
        assert content == "données factices sqlite", (
            "Contenu de chroma.sqlite3 altéré après rollback"
        )

    def test_binary_file_integrity_preserved(self, tmp_path):
        """Les fichiers binaires sont restaurés bit-pour-bit."""
        palace = self._create_palace(tmp_path)
        snapshot = self._make_tarball(palace, tmp_path)

        import shutil
        shutil.rmtree(palace)
        rollback_depuis_snapshot(palace, snapshot)

        restored = (palace / "sub" / "data.bin").read_bytes()
        assert restored == b"\x00\x01\x02\x03"


# ===========================================================================
# 9. test_rollback_missing_snapshot_logs_critical
# ===========================================================================

class TestRollbackMissingSnapshot:
    def test_inexistent_snapshot_logs_critical(self, tmp_path, caplog):
        """
        Passer un chemin de snapshot inexistant : le log doit être CRITICAL
        (ou ERROR) et mentionner le chemin, sans lever d'exception.
        """
        palace_path = tmp_path / "palace"
        palace_path.mkdir()
        fake_snapshot = tmp_path / "inexistant_backup.tar.gz"

        with caplog.at_level(logging.ERROR, logger="aria.migrate_embedder"):
            rollback_depuis_snapshot(palace_path, fake_snapshot)

        # Le chemin du snapshot absent doit apparaître dans les logs
        messages = " ".join(caplog.messages)
        assert "inexistant_backup.tar.gz" in messages, (
            f"Chemin du snapshot manquant attendu dans les logs. Logs : {caplog.messages}"
        )

    def test_inexistent_snapshot_does_not_raise(self, tmp_path):
        """Snapshot inexistant : pas d'exception, la fonction échoue en douceur."""
        palace_path = tmp_path / "palace"
        palace_path.mkdir()
        fake_snapshot = tmp_path / "ghost.tar.gz"
        # Ne doit pas lever d'exception
        rollback_depuis_snapshot(palace_path, fake_snapshot)

    def test_inexistent_snapshot_mentions_restauration_manuelle(self, tmp_path, caplog):
        """Le log pour snapshot manquant mentionne 'restauration manuelle'."""
        palace_path = tmp_path / "palace"
        palace_path.mkdir()
        fake_snapshot = tmp_path / "ghost.tar.gz"

        with caplog.at_level(logging.ERROR, logger="aria.migrate_embedder"):
            rollback_depuis_snapshot(palace_path, fake_snapshot)

        messages = " ".join(caplog.messages).lower()
        assert "restauration manuelle" in messages, (
            f"'restauration manuelle' attendu dans les logs. Logs : {caplog.messages}"
        )
