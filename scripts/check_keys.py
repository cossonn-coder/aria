import os, httpx
from dotenv import load_dotenv

load_dotenv("/home/nico/Nextcloud/projects/aria/.env")

def check(name, fn):
    try:
        result = fn()
        ok = result.startswith("OK")
        print(f"{'✅' if ok else '❌'} {name}: {result}")
    except Exception as e:
        print(f"❌ {name}: {e}")

def check_groq():
    keys = [k for k in [os.getenv("GROQ_API_KEY"), os.getenv("GROQ_API_KEY_2"), os.getenv("GROQ_API_KEY_3")] if k]
    results = []
    for i, key in enumerate(keys, 1):
        r = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5},
            timeout=10,
        )
        results.append(f"key_{i}={'OK' if r.status_code == 200 else f'HTTP {r.status_code}'}")
    return ", ".join(results) if results else "aucune clé"

def check_mistral():
    r = httpx.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('MISTRAL_API_KEY')}"},
        json={"model": "mistral-small-latest", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5},
        timeout=10,
    )
    return "OK" if r.status_code == 200 else f"HTTP {r.status_code} — {r.text[:80]}"

def check_cerebras():
    r = httpx.post(
        "https://api.cerebras.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('CEREBRAS_API_KEY')}"},
        json={"model": "llama3.1-8b", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5},
        timeout=10,
    )
    return "OK" if r.status_code == 200 else f"HTTP {r.status_code} — {r.text[:80]}"

def check_openrouter():
    r = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
        # modèles free stables en avril 2026
        json={"model": "mistralai/mistral-7b-instruct:free", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5},
        timeout=10,
    )
    return "OK" if r.status_code == 200 else f"HTTP {r.status_code} — {r.text[:80]}"

def check_gemini():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return "clé absente"
    r = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}",
        json={"contents": [{"parts": [{"text": "hi"}]}]},
        timeout=10,
    )
    return "OK" if r.status_code == 200 else f"HTTP {r.status_code} — {r.text[:80]}"

def check_pollinations():
    # sans clé — juste vérifier que le service répond
    r = httpx.get("https://image.pollinations.ai/prompt/test", timeout=15, follow_redirects=True)
    return "OK" if r.status_code == 200 else f"HTTP {r.status_code}"

check("Groq (x3)",    check_groq)
check("Mistral",      check_mistral)
check("Cerebras",     check_cerebras)
check("OpenRouter",   check_openrouter)
check("Gemini",       check_gemini)
check("Pollinations", check_pollinations)