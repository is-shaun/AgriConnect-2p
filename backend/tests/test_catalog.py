def test_list_crops_with_stats_and_search(seeded, client):
    body = client.get("/api/crops").get_json()
    names = [c["name"] for c in body["items"]]
    assert names == sorted(names) and set(names) == {"Onion", "Wheat", "Tomato", "Mustard"}
    onion = next(c for c in body["items"] if c["name"] == "Onion")
    assert onion["record_count"] > 500 and onion["market_count"] == 1 and onion["latest_avg_modal_price"] > 0
    assert client.get("/api/crops?q=whe").get_json()["items"][0]["name"] == "Wheat"
    assert client.get("/api/crops?category=Oilseeds").get_json()["pagination"]["total"] == 1


def test_get_crop_and_404(seeded, client):
    crops = client.get("/api/crops").get_json()["items"]
    crop = client.get(f"/api/crops/{crops[0]['id']}").get_json()
    assert crop["crop"]["name"] == crops[0]["name"]
    assert len(crop["latest_by_market"]) >= 1
    missing = client.get("/api/crops/9999")
    assert missing.status_code == 404 and missing.get_json()["error"]["code"] == "not_found"


def test_markets_filters(seeded, client):
    all_markets = client.get("/api/markets").get_json()
    assert all_markets["pagination"]["total"] == 3
    bihar = client.get("/api/markets?state=Bihar").get_json()["items"]
    assert [m["market_name"] for m in bihar] == ["Patna"]
    onion_id = next(c["id"] for c in client.get("/api/crops").get_json()["items"] if c["name"] == "Onion")
    onion_markets = client.get(f"/api/markets?crop_id={onion_id}").get_json()["items"]
    assert [m["market_name"] for m in onion_markets] == ["Lasalgaon"]


def test_prices_pagination_sorting_and_filters(seeded, client):
    page1 = client.get("/api/prices?per_page=5").get_json()
    assert len(page1["items"]) == 5 and page1["pagination"]["page"] == 1
    dates = [p["observation_date"] for p in page1["items"]]
    assert dates == sorted(dates, reverse=True)
    page2 = client.get("/api/prices?per_page=5&page=2").get_json()
    assert {p["id"] for p in page1["items"]}.isdisjoint({p["id"] for p in page2["items"]})
    p = page1["items"][0]
    assert p["min_price"] <= p["modal_price"] <= p["max_price"] and p["is_demo"] is True and p["unit"]

    cheap_first = client.get("/api/prices?sort=modal_price&per_page=3").get_json()["items"]
    assert cheap_first[0]["modal_price"] <= cheap_first[-1]["modal_price"]

    patna = client.get("/api/prices?district=Patna&per_page=100").get_json()
    assert patna["items"] and all(p["location"]["district"] == "Patna" for p in patna["items"])
    ranged = client.get("/api/prices?date_from=2026-01-01&date_to=2026-01-31&per_page=100").get_json()
    assert all("2026-01-01" <= p["observation_date"] <= "2026-01-31" for p in ranged["items"])
    searched = client.get("/api/prices?q=tomato").get_json()["items"]
    assert searched and all(p["crop"]["name"] == "Tomato" for p in searched)
    latest = client.get("/api/prices?latest=true").get_json()
    assert latest["pagination"]["total"] == 4  # one row per crop/market series
    assert client.get("/api/prices?is_demo=false").get_json()["pagination"]["total"] == 0


def test_prices_invalid_query_params(seeded, client):
    for qs, field in [("page=0", "page"), ("per_page=500", "per_page"), ("sort=password", "sort"),
                      ("date_from=31-01-2026", "date_from"), ("crop_id=abc", "crop_id"),
                      ("date_from=2026-02-01&date_to=2026-01-01", "date_to")]:
        resp = client.get(f"/api/prices?{qs}")
        assert resp.status_code == 422, qs
        assert field in resp.get_json()["error"]["details"]


def test_price_detail_and_history(seeded, client):
    pid = client.get("/api/prices?per_page=1").get_json()["items"][0]["id"]
    assert client.get(f"/api/prices/{pid}").get_json()["price"]["id"] == pid
    assert client.get("/api/prices/999999").status_code == 404
    wheat = next(c for c in client.get("/api/crops").get_json()["items"] if c["name"] == "Wheat")
    hist = client.get(f"/api/prices/history?crop_id={wheat['id']}&date_from=2026-01-01").get_json()
    assert hist["interval"] == "week" and len(hist["points"]) > 30
    assert all(p["date"] >= "2026-01-01" for p in hist["points"])
    daily = client.get(f"/api/prices/history?crop_id={wheat['id']}&interval=day&date_from=2026-10-01").get_json()
    assert len(daily["points"]) >= 5
    assert client.get("/api/prices/history").status_code == 422
    assert client.get("/api/prices/history?crop_id=999").status_code == 404


def test_summary_stats(seeded, client):
    s = client.get("/api/stats/summary").get_json()
    assert s["crops"] == 4 and s["markets"] == 3 and s["price_records"] == s["demo_price_records"] > 0
    assert s["verified_price_records"] == 0 and s["latest_observation_date"] == "2026-10-16"


def test_health(app, client):
    body = client.get("/api/health").get_json()
    assert body["status"] == "ok" and body["database"]["ok"] and body["model"]["available"]
