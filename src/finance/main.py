from fastapi import FastAPI

app = FastAPI(title="finance-dashboard")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
