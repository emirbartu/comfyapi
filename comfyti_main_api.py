from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
import websocket
import uuid
import json
import urllib.request
import urllib.parse
import requests
from PIL import Image
import io
import random

app = FastAPI()

# Constants
SERVER_ADDRESS = "127.0.0.1:8188"
CLIENT_ID = str(uuid.uuid4())

# Helper functions (copy from main_socket.py)
def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": CLIENT_ID}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{SERVER_ADDRESS}/prompt", data=data)
    return json.loads(urllib.request.urlopen(req).read())

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen(f"http://{SERVER_ADDRESS}/view?{url_values}") as response:
        return response.read()

def get_history(prompt_id):
    with urllib.request.urlopen(f"http://{SERVER_ADDRESS}/history/{prompt_id}") as response:
        return json.loads(response.read())

def get_images(ws, prompt):
    prompt_id = queue_prompt(prompt)['prompt_id']
    output_images = {}
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break  # Execution is done
        else:
            continue  # previews are binary data

    history = get_history(prompt_id)[prompt_id]
    for o in history['outputs']:
        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            if 'images' in node_output:
                images_output = []
                for image in node_output['images']:
                    image_data = get_image(image['filename'], image['subfolder'], image['type'])
                    images_output.append(image_data)
            output_images[node_id] = images_output

    return output_images

def upload_file(file, subfolder="", overwrite=False):
    try:
        body = {"image": file}
        data = {}

        if overwrite:
            data["overwrite"] = "true"

        if subfolder:
            data["subfolder"] = subfolder

        resp = requests.post(f"http://{SERVER_ADDRESS}/upload/image", files=body, data=data)

        if resp.status_code == 200:
            data = resp.json()
            path = data["name"]
            if "subfolder" in data and data["subfolder"] != "":
                path = f"{data['subfolder']}/{path}"
            return path
        else:
            print(f"{resp.status_code} - {resp.reason}")
    except Exception as error:
        print(error)
    return None

# API endpoints
@app.post("/process_image")
async def process_image(file: UploadFile = File(None)):
    if file:
        # Upload the image
        image_path = upload_file(file.file, "", True)
        if not image_path:
            return {"message": "Error uploading image"}
    else:
        # Use example.png as default input
        image_path = "example.png"

    # Load workflow from file
    with open("workflow_api.json", "r", encoding="utf-8") as f:
        workflow = json.load(f)

    # Set the text prompt for positive and negative CLIPTextEncode
    workflow["35"]["inputs"]["text"] = "angry cartoon character, angry eyebrows, blue haired princess"
    workflow["131"]["inputs"]["text"] = "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry , deformed,nsfw, deformed legs"

    # Set random seed
    seed = random.randint(1, 1000000000)

    # Set the image name for LoadImage node
    workflow["130"]["inputs"]["image"] = image_path

    # Set model
    workflow["12"]["inputs"]["unet_name"] = "flux1-schnell.safetensors"
    workflow["11"]["inputs"]["clip_name1"] = "t5xxl_fp16.safetensors"
    workflow["11"]["inputs"]["clip_name2"] = "clip_l.safetensors"
    workflow["10"]["inputs"]["vae_name"] = "ae.safetensors"

    # Process the image
    ws = websocket.WebSocket()
    ws.connect(f"ws://{SERVER_ADDRESS}/ws?clientId={CLIENT_ID}")
    images = get_images(ws, workflow)

    # Save and return the processed image
    for node_id in images:
        for image_data in images[node_id]:
            image = Image.open(io.BytesIO(image_data))
            output_filename = f"{node_id}-{seed}.png"
            image.save(output_filename)
            return {"message": "Image processed successfully", "output_file": output_filename}

    return {"message": "Error processing image"}

@app.get("/")
async def root():
    return {"message": "Welcome to ComfyTI API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
