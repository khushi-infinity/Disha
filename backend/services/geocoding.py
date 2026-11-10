import httpx

HEADERS = {"User-Agent": "gNani-AI/1.0 (elderly navigation assistant)"}

async def search_destination(query: str, lat: float | None = None, lon: float | None = None):
    params = {"q": query, "format": "jsonv2", "limit": 4, "addressdetails": 1}
    if lat is not None and lon is not None:
        params["viewbox"] = f"{lon-0.25},{lat+0.25},{lon+0.25},{lat-0.25}"
        params["bounded"] = 0
    async with httpx.AsyncClient(timeout=12, headers=HEADERS) as client:
        response = await client.get("https://nominatim.openstreetmap.org/search", params=params)
        response.raise_for_status()
    return [{"name": r["display_name"], "lat": float(r["lat"]), "lon": float(r["lon"]), "type": r.get("type", "place")} for r in response.json()]
