import os
from flask import Flask, render_template, request, jsonify
from scanner import inspect_file, process_inbound_folder

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"txt", "csv", "json"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/inspect", methods=["POST"])
def inspect():
    if "file" not in request.files:
        return render_template("result.html", error="No file part found in the request.")

    file = request.files["file"]

    if file.filename == "":
        return render_template("result.html", error="No file selected.")

    if not allowed_file(file.filename):
        return render_template(
            "result.html",
            error="Unsupported file type. Please upload a .txt, .csv, or .json file."
        )

    source_system = request.form.get("source_system", "").strip()
    interface_name = request.form.get("interface_name", "").strip()
    submitted_by = request.form.get("submitted_by", "").strip()
    destination_system = request.form.get("destination_system", "").strip()

    metadata = {
        "source_system": source_system,
        "interface_name": interface_name,
        "submitted_by": submitted_by,
        "destination_system": destination_system,
    }

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(file_path)

    try:
        result = inspect_file(file_path, metadata=metadata)
        return render_template("result.html", result=result, error=None)
    except Exception as e:
        return render_template("result.html", error=f"Error while inspecting file: {e}")


@app.route("/process_inbound", methods=["GET"])
def process_inbound():
    try:
        summary = process_inbound_folder(inbound_dir="inbound", base_dir=".")
        return jsonify(summary)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # make ftp-like folder structure available
    os.makedirs("inbound", exist_ok=True)
    os.makedirs("tibco", exist_ok=True)
    os.makedirs("quarantine", exist_ok=True)
    os.makedirs("rejected", exist_ok=True)

    app.run(host="127.0.0.1", port=5050, debug=True, use_reloader=False)