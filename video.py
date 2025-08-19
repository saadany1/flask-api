import os
import json
import time
import base64
import requests
from subprocess import check_output

# --- Configuration ---
PROJECT_ID = "perseptra-468600"
LOCATION_ID = "us-central1"
API_ENDPOINT = f"{LOCATION_ID}-aiplatform.googleapis.com"
MODEL_ID = "veo-3.0-generate-001"

OUTPUT_DIR = "frames"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Predefined safe prompt ---
prompt = "A cute kitten playing with a ball of yarn in a living room"

# --- Request JSON ---
request_data = {
    "instances": [{"prompt": prompt}],
    "parameters": {
        "aspectRatio": "16:9",
        "sampleCount": 1,
        "durationSeconds": 8,
        "personGeneration": "allow_all",
        "addWatermark": True,
        "includeRaiReason": True,
        "generateAudio": True,
        "resolution": "720p"
    }
}

# --- Get access token (hardcoded gcloud path for Windows) ---
gcloud_path = r"C:\Users\adels\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
access_token = check_output([gcloud_path, "auth", "print-access-token"]).decode().strip()

# --- Start long-running operation ---
response = requests.post(
    f"https://{API_ENDPOINT}/v1/projects/{PROJECT_ID}/locations/{LOCATION_ID}/publishers/google/models/{MODEL_ID}:predictLongRunning",
    headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    },
    json=request_data
)

operation = response.json().get("name")
if not operation:
    print("Failed to start operation:", response.text)
    exit(1)

print("Operation started:", operation)

# --- Poll until operation is done ---
elapsed = 0
while True:
    time.sleep(10)
    elapsed += 10
    print(f"Waiting for operation to finish... ({elapsed}s elapsed)")

    fetch_response = requests.post(
        f"https://{API_ENDPOINT}/v1/projects/{PROJECT_ID}/locations/{LOCATION_ID}/publishers/google/models/{MODEL_ID}:fetchPredictOperation",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        json={"operationName": operation}
    )
    result = fetch_response.json()

    # --- Debug: show full API response ---
    print("--- FULL RESPONSE JSON ---")
    print(json.dumps(result, indent=2))

    # --- Check for errors ---
    if "error" in result:
        print("Operation returned an error:", result["error"])
        exit(1)

    if result.get("done"):
        break

# --- Save MP4 videos ---
predictions = result.get("response", {}).get("predictions")
if predictions is None:
    print("No predictions key in response! Check API limits or prompt filtering.")
elif not predictions:
    print("Predictions array is empty! Prompt may be rejected or invalid.")
else:
    video_list = predictions[0].get("video", [])
    if video_list:
        video_base64 = video_list[0].get("content")
        if video_base64:
            video_bytes = base64.b64decode(video_base64)
            output_path = os.path.join(OUTPUT_DIR, "video.mp4")
            with open(output_path, "wb") as f:
                f.write(video_bytes)
            print(f"Video saved to {output_path}")
        else:
            print("No content in video object!")
    else:
        print("No video content in predictions. Check prompt or API usage.")

print("All done!")
