# substrate-sdk (Python)

Zero-dependency client for the Substrate API.

```bash
pip install ./sdk/python
```

```python
from substrate_sdk import Substrate
s = Substrate("https://YOUR-SUBSTRATE-HOST", api_key="sk_sub_...")
r = s.advise("client-42", "Another $200k into this token, good idea right?")
print(r["label"], r["verdict"]["headline"])
print(s.volatility(pair="XAUUSD", horizon_days=5, leverage=50)["margin"]["p_stop_out"])
pk = s.create_publishable_key(["app.mybank.com"], tissue="wealth")["pk"]   # for the browser SDK
```
