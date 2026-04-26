# tests/memory/test_memory_layers.py
#
# Vérifie l'architecture mémoire 3 couches d'ARIA.
#
# Ce qu'on teste :
#   store_interaction   → écrit dans wing="aria_episodic"
#   store_semantic_fact → écrit dans wing="aria_semantic"
#   store_image_artifact → écrit dans wing="aria_episodic" avec bon type
#   retrieve_memories   → lit aria_episodic par défaut
#   retrieve_semantic   → lit aria_semantic
#   retrieve_by_intent  → filtre sur aria_episodic + room=intent_id
#
# Stratégie de mock :
#   ChromaDB est mocké via get_collection().
#   On inspecte les appels upsert() pour vérifier le schéma de métadonnées.
#   On mocke search() pour tester les fonctions de lecture.

import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone

from memory.mempalace_writer import (
    store_interaction,
    store_semantic_fact,
    store_image_artifact,
)
from memory.mempalace_bridge import (
    retrieve_memories,
    retrieve_semantic,
    retrieve_by_intent,
)
from images.image_types import ImageArtifact


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_collection_mock():
    """Mock de la collection ChromaDB — capture les appels upsert()."""
    col = MagicMock()
    col.upsert = MagicMock()
    return col


def extract_upsert_metadata(col_mock) -> dict:
    """Extrait les métadonnées du premier appel upsert sur le mock."""
    assert col_mock.upsert.called, "upsert() n'a pas été appelé"
    call_kwargs = col_mock.upsert.call_args
    metadatas = call_kwargs[1].get("metadatas") or call_kwargs[0][2]
    return metadatas[0]


def extract_upsert_document(col_mock) -> str:
    """Extrait le texte indexé du premier appel upsert."""
    call_kwargs = col_mock.upsert.call_args
    documents = call_kwargs[1].get("documents") or call_kwargs[0][0]
    return documents[0]


# ── Tests : store_interaction ─────────────────────────────────────────────────

class TestStoreInteraction:

    @patch("memory.mempalace_writer.get_collection")
    def test_writes_to_aria_episodic_wing(self, mock_get_col):
        """
        store_interaction doit écrire dans wing="aria_episodic".

        Migration : l'ancien code écrivait dans wing="aria".
        Toutes les nouvelles interactions vont dans aria_episodic.
        """
        col = make_collection_mock()
        mock_get_col.return_value = col

        store_interaction("USER:\ntest\nARIA:\nréponse", intent_id="intent-001")

        meta = extract_upsert_metadata(col)
        assert meta["wing"] == "aria_episodic", (
            f"store_interaction écrit dans wing='{meta['wing']}' "
            "au lieu de 'aria_episodic'."
        )

    @patch("memory.mempalace_writer.get_collection")
    def test_room_equals_intent_id(self, mock_get_col):
        """
        Le room doit être l'intent_id — pour le recall ciblé par projet.
        """
        col = make_collection_mock()
        mock_get_col.return_value = col

        store_interaction("échange test", intent_id="intent-jardin-42")

        meta = extract_upsert_metadata(col)
        assert meta["room"] == "intent-jardin-42"

    @patch("memory.mempalace_writer.get_collection")
    def test_type_is_interaction(self, mock_get_col):
        """Le type doit être 'interaction' pour les échanges texte."""
        col = make_collection_mock()
        mock_get_col.return_value = col

        store_interaction("échange", intent_id="intent-001")

        meta = extract_upsert_metadata(col)
        assert meta["type"] == "interaction"

    @patch("memory.mempalace_writer.get_collection")
    def test_timestamp_is_isoformat_string(self, mock_get_col):
        """
        ChromaDB n'accepte que str, int, float, bool, None.
        Le timestamp doit être une string isoformat — jamais un datetime.
        """
        col = make_collection_mock()
        mock_get_col.return_value = col

        store_interaction("échange", intent_id="intent-001")

        meta = extract_upsert_metadata(col)
        assert isinstance(meta["timestamp"], str)
        # Vérifie que c'est un isoformat parseable
        datetime.fromisoformat(meta["timestamp"])

    @patch("memory.mempalace_writer.get_collection")
    def test_custom_metadata_merged(self, mock_get_col):
        """Les métadonnées supplémentaires doivent être fusionnées."""
        col = make_collection_mock()
        mock_get_col.return_value = col

        store_interaction(
            "échange",
            intent_id="intent-001",
            metadata={"intent_name": "jardin", "source": "llm_execution_router"},
        )

        meta = extract_upsert_metadata(col)
        assert meta["intent_name"] == "jardin"
        assert meta["source"] == "llm_execution_router"


# ── Tests : store_semantic_fact ───────────────────────────────────────────────

class TestStoreSemanticFact:

    @patch("memory.mempalace_writer.get_collection")
    def test_writes_to_aria_semantic_wing(self, mock_get_col):
        """
        store_semantic_fact doit écrire dans wing="aria_semantic".

        La couche sémantique est distincte de la couche épisodique :
        les faits stables ne doivent pas être mélangés aux événements.
        """
        col = make_collection_mock()
        mock_get_col.return_value = col

        store_semantic_fact("Nico est allergique au gluten", subject="santé")

        meta = extract_upsert_metadata(col)
        assert meta["wing"] == "aria_semantic"

    @patch("memory.mempalace_writer.get_collection")
    def test_room_equals_subject(self, mock_get_col):
        """
        Le room doit être le subject — pour le recall ciblé par domaine.

        retrieve_semantic("santé") retrouve les faits sur la santé,
        retrieve_semantic("localisation") les faits de localisation, etc.
        """
        col = make_collection_mock()
        mock_get_col.return_value = col

        store_semantic_fact("Nico habite Seyssinet-Pariset", subject="localisation")

        meta = extract_upsert_metadata(col)
        assert meta["room"] == "localisation"

    @patch("memory.mempalace_writer.get_collection")
    def test_type_is_semantic_fact(self, mock_get_col):
        """Le type doit être 'semantic_fact'."""
        col = make_collection_mock()
        mock_get_col.return_value = col

        store_semantic_fact("Nico pratique l'escalade", subject="activités")

        meta = extract_upsert_metadata(col)
        assert meta["type"] == "semantic_fact"

    @patch("memory.mempalace_writer.get_collection")
    def test_fact_text_is_indexed(self, mock_get_col):
        """Le texte du fait doit être le document indexé."""
        col = make_collection_mock()
        mock_get_col.return_value = col

        store_semantic_fact("Nico est végétarien", subject="alimentation")

        text = extract_upsert_document(col)
        assert text == "Nico est végétarien"

    @patch("memory.mempalace_writer.get_collection")
    def test_source_default_is_conversation(self, mock_get_col):
        """Source par défaut = 'conversation'."""
        col = make_collection_mock()
        mock_get_col.return_value = col

        store_semantic_fact("un fait", subject="test")

        meta = extract_upsert_metadata(col)
        assert meta["source"] == "conversation"


# ── Tests : store_image_artifact ─────────────────────────────────────────────

class TestStoreImageArtifact:

    def make_artifact(self, source: str, caption=None, prompt=None, path=None) -> ImageArtifact:
        return ImageArtifact(
            source=source,
            path=path or "/tmp/test.jpg",
            caption=caption,
            prompt=prompt,
            intent_id=None,
            timestamp=datetime.now(timezone.utc),
        )

    @patch("memory.mempalace_writer.get_collection")
    def test_image_input_writes_to_episodic(self, mock_get_col):
        """Une image reçue doit être stockée dans aria_episodic."""
        col = make_collection_mock()
        mock_get_col.return_value = col

        artifact = self.make_artifact(source="input", caption="belle courge")
        store_image_artifact(artifact, intent_id="intent-jardin")

        meta = extract_upsert_metadata(col)
        assert meta["wing"] == "aria_episodic"

    @patch("memory.mempalace_writer.get_collection")
    def test_image_input_type(self, mock_get_col):
        """Une image reçue doit avoir type='image_input'."""
        col = make_collection_mock()
        mock_get_col.return_value = col

        artifact = self.make_artifact(source="input", caption="photo jardin")
        store_image_artifact(artifact)

        meta = extract_upsert_metadata(col)
        assert meta["type"] == "image_input"

    @patch("memory.mempalace_writer.get_collection")
    def test_image_generated_type(self, mock_get_col):
        """Une image générée doit avoir type='image_generated'."""
        col = make_collection_mock()
        mock_get_col.return_value = col

        artifact = self.make_artifact(source="generated", prompt="un jardin en été")
        store_image_artifact(artifact)

        meta = extract_upsert_metadata(col)
        assert meta["type"] == "image_generated"

    @patch("memory.mempalace_writer.get_collection")
    def test_generated_image_indexes_prompt(self, mock_get_col):
        """
        Pour une image générée, c'est le prompt qui est indexé —
        pas la caption (qui peut être vide).

        Permet de retrouver "montre-moi les images de mon jardin"
        par similarité avec le prompt original.
        """
        col = make_collection_mock()
        mock_get_col.return_value = col

        artifact = self.make_artifact(source="generated", prompt="jardin potager été")
        store_image_artifact(artifact)

        text = extract_upsert_document(col)
        assert "jardin potager été" in text

    @patch("memory.mempalace_writer.get_collection")
    def test_input_image_indexes_caption(self, mock_get_col):
        """
        Pour une image reçue, c'est la description vision qui est indexée.
        """
        col = make_collection_mock()
        mock_get_col.return_value = col

        artifact = self.make_artifact(source="input", caption="une courge bien verte")
        store_image_artifact(artifact)

        text = extract_upsert_document(col)
        assert "une courge bien verte" in text

    @patch("memory.mempalace_writer.get_collection")
    def test_no_write_if_no_indexable_text(self, mock_get_col):
        """
        Si ni caption ni prompt ne sont disponibles, on n'écrit rien.
        Évite les entrées vides sans valeur sémantique en ChromaDB.
        """
        col = make_collection_mock()
        mock_get_col.return_value = col

        artifact = self.make_artifact(source="input", caption=None, prompt=None)
        store_image_artifact(artifact)

        col.upsert.assert_not_called()

    @patch("memory.mempalace_writer.get_collection")
    def test_intent_id_sets_room(self, mock_get_col):
        """L'intent_id doit être utilisé comme room."""
        col = make_collection_mock()
        mock_get_col.return_value = col

        artifact = self.make_artifact(source="generated", prompt="test")
        store_image_artifact(artifact, intent_id="intent-jardin-99")

        meta = extract_upsert_metadata(col)
        assert meta["room"] == "intent-jardin-99"

    @patch("memory.mempalace_writer.get_collection")
    def test_no_intent_uses_general_room(self, mock_get_col):
        """Sans intent_id, room='general' est utilisé comme fallback."""
        col = make_collection_mock()
        mock_get_col.return_value = col

        artifact = self.make_artifact(source="generated", prompt="test sans intent")
        store_image_artifact(artifact, intent_id=None)

        meta = extract_upsert_metadata(col)
        assert meta["room"] == "general"


# ── Tests : retrieve_memories ─────────────────────────────────────────────────

class TestRetrieveMemories:

    @patch("memory.mempalace_bridge.search")
    def test_default_wing_is_episodic(self, mock_search):
        """
        retrieve_memories doit cibler aria_episodic par défaut.

        Migration : l'ancien code ciblait wing="aria".
        """
        mock_search.return_value = {"results": []}

        retrieve_memories("test query")

        call_kwargs = mock_search.call_args[1]
        assert call_kwargs["wing"] == "aria_episodic"

    @patch("memory.mempalace_bridge.search")
    def test_n_zero_returns_empty(self, mock_search):
        """n=0 doit retourner vide sans appeler ChromaDB."""
        result = retrieve_memories("query", n=0)

        mock_search.assert_not_called()
        assert result["hits"] == []
        assert result["count"] == 0

    @patch("memory.mempalace_bridge.search")
    def test_filters_high_distance(self, mock_search):
        """
        Les résultats avec distance >= 0.8 doivent être filtrés.
        Un souvenir trop distant n'est pas pertinent.
        """
        mock_search.return_value = {
            "results": [
                {"text": "pertinent", "distance": 0.3, "room": "intent-001"},
                {"text": "trop loin", "distance": 0.9, "room": "intent-001"},
            ]
        }

        result = retrieve_memories("query", n=5)

        assert result["count"] == 1
        assert result["hits"][0]["text"] == "pertinent"

    @patch("memory.mempalace_bridge.search")
    def test_filters_general_room(self, mock_search):
        """
        Les résultats de room='general' doivent être exclus.
        Ce room est trop peu spécifique pour le contexte cognitif.
        """
        mock_search.return_value = {
            "results": [
                {"text": "spécifique", "distance": 0.3, "room": "intent-001"},
                {"text": "générique", "distance": 0.3, "room": "general"},
            ]
        }

        result = retrieve_memories("query", n=5)

        assert result["count"] == 1
        assert result["hits"][0]["text"] == "spécifique"

    @patch("memory.mempalace_bridge.search")
    def test_custom_wing_is_passed_through(self, mock_search):
        """
        On peut cibler une wing spécifique, ex: "aria" pour les anciennes entrées.
        """
        mock_search.return_value = {"results": []}

        retrieve_memories("query", wing="aria")

        call_kwargs = mock_search.call_args[1]
        assert call_kwargs["wing"] == "aria"


# ── Tests : retrieve_semantic ─────────────────────────────────────────────────

class TestRetrieveSemantic:

    @patch("memory.mempalace_bridge.search")
    def test_targets_aria_semantic_wing(self, mock_search):
        """retrieve_semantic doit toujours cibler aria_semantic."""
        mock_search.return_value = {"results": []}

        retrieve_semantic("allergie gluten")

        call_kwargs = mock_search.call_args[1]
        assert call_kwargs["wing"] == "aria_semantic"

    @patch("memory.mempalace_bridge.search")
    def test_subject_filter_passed_as_room(self, mock_search):
        """Le subject optionnel doit être passé comme room."""
        mock_search.return_value = {"results": []}

        retrieve_semantic("santé", subject="santé")

        call_kwargs = mock_search.call_args[1]
        assert call_kwargs["room"] == "santé"

    @patch("memory.mempalace_bridge.search")
    def test_no_subject_passes_none_room(self, mock_search):
        """Sans subject, room=None — recherche dans toute la couche sémantique."""
        mock_search.return_value = {"results": []}

        retrieve_semantic("préférences")

        call_kwargs = mock_search.call_args[1]
        assert call_kwargs["room"] is None


# ── Tests : retrieve_by_intent ────────────────────────────────────────────────

class TestRetrieveByIntent:

    @patch("memory.mempalace_bridge.search")
    def test_targets_aria_episodic(self, mock_search):
        """retrieve_by_intent doit cibler aria_episodic."""
        mock_search.return_value = {"results": []}

        retrieve_by_intent("query", intent_id="intent-jardin")

        call_kwargs = mock_search.call_args[1]
        assert call_kwargs["wing"] == "aria_episodic"

    @patch("memory.mempalace_bridge.search")
    def test_room_equals_intent_id(self, mock_search):
        """Le room doit être l'intent_id pour le recall ciblé."""
        mock_search.return_value = {"results": []}

        retrieve_by_intent("query", intent_id="intent-maison-123")

        call_kwargs = mock_search.call_args[1]
        assert call_kwargs["room"] == "intent-maison-123"

    @patch("memory.mempalace_bridge.search")
    def test_returns_all_results_without_distance_filter(self, mock_search):
        """
        retrieve_by_intent ne filtre PAS par distance.

        Contrairement à retrieve_memories, on veut tout ce qui est
        lié à l'intent — même les souvenirs un peu éloignés thématiquement
        mais qui appartiennent au même projet.
        """
        mock_search.return_value = {
            "results": [
                {"text": "proche", "distance": 0.2},
                {"text": "moins proche", "distance": 0.75},
                {"text": "loin", "distance": 0.95},
            ]
        }

        result = retrieve_by_intent("query", intent_id="intent-001")

        assert result["count"] == 3