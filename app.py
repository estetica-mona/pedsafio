from flask import Flask, request, jsonify
from gofile_module import convert_url_to_direct_links, GoFile
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "message": "GoFile converter API. POST /convert with JSON {\"urls\": [...] }"})


@app.route("/convert", methods=["POST"])
def convert():
    data = request.get_json(force=True)
    if not data or "urls" not in data:
        return jsonify({"status": "error", "message": "JSON body must include 'urls' list"}), 400

    urls = data.get("urls")
    if not isinstance(urls, list):
        return jsonify({"status": "error", "message": "'urls' must be a list"}), 400

    if len(urls) == 0:
        return jsonify({"status": "error", "message": "Provide at least one GoFile URL"}), 400

    if len(urls) > 3:
        return jsonify({"status": "error", "message": "Maximum 3 URLs allowed"}), 400

    password = data.get("password")
    results = []
    for url in urls:
        try:
            links = convert_url_to_direct_links(url, password=password, max_results=50)
            results.append({"input": url, "direct_links": links})
        except Exception as e:
            results.append({"input": url, "error": str(e)})

    return jsonify({"status": "ok", "results": results})


@app.route("/convert_fixed", methods=["GET", "POST"])
def convert_fixed():
    """Convierte exactamente estas 3 URLs y devuelve 3 enlaces directos enumerados.

    Etiquetas y URLs (fijas):
    - Standard: https://gofile.io/d/en4HXu
    - Enhanced: https://gofile.io/d/YbiRbg
    - Potato:   https://gofile.io/d/mnaS35

    Si se envía JSON POST con {"password": "..."} se usará esa contraseña para los 3 enlaces.
    """
    # URLs fijas solicitadas
    fixed = {
        "Standard": "https://gofile.io/d/en4HXu",
        "Enhanced": "https://gofile.io/d/YbiRbg",
        "Potato": "https://gofile.io/d/mnaS35",
    }

    # permitir password opcional por POST JSON o por query param
    password = None
    if request.method == "POST":
        try:
            data = request.get_json(force=True)
            password = data.get("password") if isinstance(data, dict) else None
        except Exception:
            password = None
    else:
        password = request.args.get("password")

    # Ejecutar conversiones en paralelo para reducir latencia
    results = {}
    with ThreadPoolExecutor(max_workers=3) as ex:
        future_map = {ex.submit(convert_url_to_direct_links, url, password, 5): label for label, url in fixed.items()}
        for fut in as_completed(future_map):
            label = future_map[fut]
            try:
                links = fut.result(timeout=8)
                results[label] = {"links": links, "direct": (links[0] if links else None)}
            except TimeoutError:
                results[label] = {"links": [], "direct": None, "error": "timeout"}
            except Exception as e:
                results[label] = {"links": [], "direct": None, "error": str(e)}

    # Formato de salida: enumerado y exactamente 3 items
    enumerated = {
        "1": {"label": "Standard", **results.get("Standard", {})},
        "2": {"label": "Enhanced", **results.get("Enhanced", {})},
        "3": {"label": "Potato", **results.get("Potato", {})},
    }

    return jsonify({"status": "ok", "results": enumerated})


if __name__ == "__main__":
    # Pre-warm GoFile token/wt and HTTP session to reduce first-request latency
    try:
        gf = GoFile()
        # attempt to prewarm synchronously; if it fails we still run the server
        gf.update_token()
        gf.update_wt()
    except Exception as e:
        # log but continue; first requests may take slightly longer
        import logging
        logging.getLogger("GoFile").warning(f"prewarm failed: {e}")

    app.run(host="0.0.0.0", port=5000, debug=True)

