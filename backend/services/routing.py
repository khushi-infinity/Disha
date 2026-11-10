import httpx
from math import radians, sin, cos, sqrt, atan2

def metres(a, b):
    r=6371000; dlat=radians(b[0]-a[0]); dlon=radians(b[1]-a[1]); x=sin(dlat/2)**2+cos(radians(a[0]))*cos(radians(b[0]))*sin(dlon/2)**2
    return 2*r*atan2(sqrt(x),sqrt(1-x))

def simple_step(step):
    m=round(step.get("distance", 0)); modifier=step.get("maneuver", {}).get("modifier", "")
    typ=step.get("maneuver", {}).get("type", "continue")
    name=step.get("name") or "raasta"
    if typ in ("arrive", "destination"): return "Aap apni manzil par pahunch gaye hain."
    if typ in ("turn", "end of road") and modifier:
        side = "baayein" if modifier == "left" else "daayein" if modifier == "right" else modifier
        return f"Lagbhag {m} meter ke baad {side} mudiyega, {name} par. Sadak paar karne se pehle traffic zaroor dekhiye."
    return f"Lagbhag {m} meter {name} par seedha chaliye."

async def pedestrian_route(origin_lat, origin_lon, destination_lat, destination_lon):
    url=f"https://router.project-osrm.org/route/v1/foot/{origin_lon},{origin_lat};{destination_lon},{destination_lat}"
    async with httpx.AsyncClient(timeout=18) as client:
        response=await client.get(url, params={"overview":"full","geometries":"geojson","steps":"true"})
        response.raise_for_status(); data=response.json()
    if data.get("code") != "Ok" or not data.get("routes"): raise ValueError("A safe walking route could not be found.")
    route=data["routes"][0]; steps=[simple_step(s) for leg in route["legs"] for s in leg["steps"]]
    return {"distance_m": round(route["distance"]), "duration_s": round(route["duration"]), "steps": steps, "geometry": route["geometry"]}
