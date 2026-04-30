# aria/llm/image_gen/hf_client.py
#
# Client de génération image via HuggingFace Inference API.
#
# Auth :
#   L'Inference API HF est une API HTTP standard — l'auth se fait via
#   le header "Authorization: Bearer <token>", pas via os.environ["HF_TOKEN"]
#   (ce mécanisme est réservé aux libs Hub comme sentence-transformers).
#   Le token est résolu dans cet ordre :
#     1. api_key passé au constructeur (wiring explicite depuis Config)
#     2. HF_TOKEN dans l'environnement (fallback défensif)
#     3. HUGGINGFACE_HUB_TOKEN dans l'environnement (alias alternatif)
#     4. None → requête anonyme, rate-limit bas
#
# Problèmes corrigés :
#   1. Double préfixe models/models/ dans l'URL → 404 systématique.
#      Fix : base_url.removesuffix("/models") dans le constructeur.
#
#   2. Pas de fallback vers l'environnement si api_key non passé.
#      Fix : résolution en cascade api_key → HF_TOKEN → HUGGINGFACE_HUB_TOKEN.
#
#   3. Pas de retry sur HTTP 503 (cold start modèle HF).
#      Les modèles HF gratuits sont déchargés après inactivité — la première
#      requête retourne 503 pendant le chargement (jusqu'à ~20s).
#      Fix : retry avec backoff jusqu'à MAX_RETRIES tentatives.
#
#   4. Écriture aveugle de r.content dans un .png même si HF retourne
#      un JSON d'erreur ou de modération.
#      Fix : vérification du content-type avant écriture.

import hashlib
import os
import time
import httpx
from pathlib import Path


# Nombre maximal de tentatives sur HTTP 503 (cold start modèle)
MAX_RETRIES = 5

# Délai en secondes entre chaque retry 503
RETRY_DELAY_SECONDS = 3


class HuggingFaceImageClient:
    """
    Client de génération image via HuggingFace Inference API.

    Gratuit avec rate limiting.
    Avec HF_TOKEN : meilleur quota et accès aux modèles gated.
    Sans token    : fonctionne en anonyme mais plus lentement.

    Args:
        base_url   : racine de l'API HF, sans /models.
                     Valeur attendue : "https://api-inference.huggingface.co"
        model      : identifiant du modèle HF (ex: "black-forest-labs/FLUX.1-schnell")
        output_dir : répertoire local de sauvegarde des images générées
        api_key    : HF token explicite (optionnel — fallback vers env si absent)
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        output_dir: str,
        api_key: str | None = None,
        **_,
    ):
        # Normalisation défensive : retire un éventuel suffixe /models
        # pour éviter le double préfixe si la config est mal formée.
        self.base_url = base_url.rstrip("/").removesuffix("/models")
        self.model    = model

        # Résolution du token en cascade :
        # wiring explicite > variable d'environnement HF_TOKEN > alias alternatif
        # Le header Authorization est le seul mécanisme d'auth pour l'Inference API.
        # os.environ["HF_TOKEN"] n'est utile qu'aux libs Hub (sentence-transformers).
        self.api_key = (
            api_key
            or os.getenv("HF_TOKEN")
            or os.getenv("HUGGINGFACE_HUB_TOKEN")
        )

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, prompt: str) -> "GenerationResult":
        """
        Génère une image depuis un prompt texte.

        Gère le cold start HF : retry automatique sur HTTP 503
        jusqu'à MAX_RETRIES tentatives avec délai RETRY_DELAY_SECONDS.

        Args:
            prompt : texte décrivant l'image (peut être enrichi par _inject_context)

        Returns:
            GenerationResult avec path local et caption

        Raises:
            RuntimeError : si la réponse HF n'est pas une image (JSON erreur, modération)
            httpx.HTTPStatusError : si le serveur retourne une erreur non-récupérable
        """
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = f"{self.base_url}/models/{self.model}"

        r = self._post_with_retry(url, headers, prompt)

        # ── Vérification content-type ────────────────────────────────────────
        # HF peut retourner un JSON d'erreur, de quota, ou de modération
        # avec un status 200. Écrire ce JSON dans un .png produirait un
        # fichier corrompu silencieusement.
        content_type = r.headers.get("content-type", "")
        if "image" not in content_type:
            raise RuntimeError(
                f"HuggingFace a retourné un contenu non-image "
                f"(content-type: {content_type!r}) : {r.text[:200]}"
            )

        slug     = hashlib.md5(prompt.encode()).hexdigest()[:12]
        filename = self.output_dir / f"aria_hf_{slug}.png"
        filename.write_bytes(r.content)

        return GenerationResult(
            path=str(filename),
            caption=f"[generated via HF: {prompt[:60]}]",
        )

    def _post_with_retry(
        self,
        url: str,
        headers: dict,
        prompt: str,
    ) -> httpx.Response:
        """
        Effectue la requête POST avec retry sur HTTP 503 (cold start).

        Les modèles HF gratuits sont déchargés après inactivité.
        La première requête retourne 503 le temps du rechargement (~5-20s).
        On retente jusqu'à MAX_RETRIES fois avec un délai fixe.

        Returns:
            httpx.Response avec status 2xx

        Raises:
            httpx.HTTPStatusError : si toutes les tentatives échouent
        """
        last_response = None

        for attempt in range(MAX_RETRIES):
            r = httpx.post(
                url,
                headers=headers,
                json={"inputs": prompt},
                timeout=120,
            )

            if r.status_code == 503:
                # Cold start — on attend et on réessaie
                last_response = r
                print(
                    f"[HF CLIENT] 503 cold start "
                    f"(tentative {attempt + 1}/{MAX_RETRIES}) "
                    f"— retry dans {RETRY_DELAY_SECONDS}s"
                )
                time.sleep(RETRY_DELAY_SECONDS)
                continue

            # Tout autre statut : raise si erreur, retourner si succès
            r.raise_for_status()
            return r

        # Toutes les tentatives ont échoué sur 503
        last_response.raise_for_status()


class GenerationResult:
    """Résultat d'une génération image — path local + caption courte."""

    def __init__(self, path: str, caption: str):
        self.path    = path
        self.caption = caption