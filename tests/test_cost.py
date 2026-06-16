from lib.cost import estimate_jpy

def test_estimate_jpy_basic():
    # inTok = ceil(1000*0.7)=700; usd = 700/1e6*3 + 2000/1e6*15 = 0.0321; yen = round(0.0321*150)=5
    assert estimate_jpy(1000, 2000) == 5

def test_estimate_jpy_floor_one():
    assert estimate_jpy(0, 0) == 1
