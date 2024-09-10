from flask import Flask, request, render_template
from werkzeug.utils import secure_filename
import os
import requests
import moviepy.editor as mp
import speech_recognition as sr
import os
import json
import google.generativeai as genai

from dotenv import load_dotenv

load_dotenv()  # Load variables from .en

app = Flask(__name__)
apikey=os.getenv('API_KEY')
tab_key=os.getenv('TAB_KEY')
tab_token=os.getenv('TAB_TOKEN')
list_key=os.getenv('LIST_KEY')


# Configurar la carpeta donde se guardarán los archivos (static)
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

url = "https://api.trello.com/1/cards"

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
            return render_template('index.html', mensaje="Video Guardado", accion="Generar Transcripcion", show_borrar="true")
    return render_template('upload.html')
    
    
@app.route('/delete', methods=['POST'])
def removeVideo():
    try:
        # Ruta absoluta a la carpeta donde se encuentran los archivos
        ruta_archivos = "./"  # Reemplaza con la ruta correcta

        # Construye las rutas completas a los archivos
        ruta_video = os.path.join(ruta_archivos+"static/uploads", "video.mp4")
        ruta_transcripcion = os.path.join(ruta_archivos, "./transcripcion.txt")
        ruta_wav = os.path.join(ruta_archivos, "./audio.wav")

        # Elimina los archivos si existen
        if os.path.exists(ruta_video):
            os.remove(ruta_video)
            print("Archivo video.mp4 eliminado.")
        if os.path.exists(ruta_transcripcion):
            os.remove(ruta_transcripcion)
            print("Archivo transcripcion.txt eliminado.")
        if os.path.exists(ruta_wav):
            os.remove(ruta_wav)
            print("Archivo audio.wav eliminado.")
        return render_template('index.html', mensaje="Video Borrado")
    except OSError as error:
        return render_template('index.html', mensaje="Error en el Borrado", accion="-", show_borrar="true")

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
        for  i in range(3):
            query = {
            'idList': list_key,
            'key': tab_key,
            'token': tab_token,
            'name': data[i]["titulo"],
            'desc': data[i]["descripcion"]
            }

            response = requests.request(
                "POST",
                url,
                headers=headers,
                params=query
            )

        return render_template('index.html', mensaje="Tareas Creada", accion="Generar Tareas", show_borrar="true"),200
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
                return render_template('index.html', mensaje="Transcripcion Creada", accion="Crear Tarea", show_borrar="true")
            except sr.UnknownValueError:
                print("No se pudo entender el audio.")
            except sr.RequestError as e:
                print(f"No se pudo completar la solicitud: {e}")
        