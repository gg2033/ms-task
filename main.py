from flask import Flask, request, render_template
from werkzeug.utils import secure_filename
import os
import requests
import moviepy.editor as mp
import speech_recognition as sr
import os
import json
import google.generativeai as genai


app = Flask(__name__)
app.config.from_pyfile('./settings.py')
apikey=app.config['API_KEY']
tab_key=app.config['TAB_KEY']
tab_token=app.config['TAB_TOKEN']


# Configurar la carpeta donde se guardarán los archivos (static)
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

url = "https://api.trello.com/1/cards"
print("LA  API KEY ES " + apikey)
genai.configure(api_key=apikey)

# Especifica el ID del tablero y la lista
board_id = 'prueba-ia'
list_id = 'task-ai'

# Nombre del archivo de transcripción
transcription_file = "transcripcion.txt"

model = genai.GenerativeModel('gemini-1.5-flash',
                              # Set the `response_mime_type` to output JSON
                              generation_config={"response_mime_type": "application/json"})


@app.route("/", methods=['GET'])
def hello_world():
    return render_template('index.html')

@app.route('/upload', methods=['POST', 'GET'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
             return render_template('index.html', mensaje='No file part')
        file = request.files['file']
        if file.filename == '':
            return render_template('index.html', mensaje='No selected file')
        if file:
            filename = secure_filename("video.mp4")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # Aquí puedes realizar el procesamiento del video
            # Por ejemplo, moverlo a un bucket de S3
            # o analizarlo con OpenCV
            return render_template('index.html', mensaje="Video Guardado")
    return render_template('upload.html')
    
    
@app.route('/task', methods=['POST'])
def generateTask():
    if os.path.exists(transcription_file):
        # Leer el contenido del archivo
        with open(transcription_file, "r", encoding="utf-8") as file:
            text = file.read()

        prompt = "Crea tareas como para hacer un desarrollo de una aplicacion dado  un texto, en esquema json: Tarea = {titulo: str, descripcion: str} Devolver `list[Tarea]`. El texto es: "+text+"."
        # Llamar a la API de ChatGPT
        response = model.generate_content(prompt)
        json_string = response.text.strip()

        # Convertir la respuesta a un objeto Python
        data = json.loads(json_string)
        print(data)
        headers = {
        "Accept": "application/json"
        }

        query = {
        'idList': '66d703a4d83cac99a905bdfa',
        'key': tab_key,
        'token': tab_token,
        'name': data[0]["titulo"],
        'desc': data[0]["descripcion"]
        }

        response = requests.request(
            "POST",
            url,
            headers=headers,
            params=query
        )


        print(response.text)

        return render_template('index.html', mensaje="Tarea Creada")
    else:
        # Nombre del archivo de video en el mismo directorio
        video_file = "./static/uploads/video.mp4"

        # Cargar el video y extraer el audio
        video = mp.VideoFileClip(video_file)
        audio = video.audio
        audio_file = "audio.wav"
        audio.write_audiofile(audio_file)

        # Inicializar el reconocedor de voz
        recognizer = sr.Recognizer()

        # Leer el archivo de audio
        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source, duration=5)
            
            # Transcribir el audio a texto
            try:
                text = recognizer.recognize_google(audio_data, language='es-ES')  # Cambia 'es-ES' si es otro idioma
                with open("transcripcion.txt", "w", encoding="utf-8") as text_file:
                    text_file.write(text)
                print("Transcripción completa y guardada en 'transcripcion.txt'.")
                return render_template('index.html', mensaje="Transcripcion Creada")
            except sr.UnknownValueError:
                print("No se pudo entender el audio.")
            except sr.RequestError as e:
                print(f"No se pudo completar la solicitud: {e}")
        