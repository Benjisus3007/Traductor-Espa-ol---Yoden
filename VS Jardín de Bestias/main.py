import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

# --- 1. CONFIGURACIÓN INICIAL Y RUTAS ROBUSTAS ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: No se encontró la clave de API de Gemini. Asegúrate de configurar el archivo .env correctamente.")
    exit()

client = genai.Client(api_key=api_key)

# Localización automática del JSON en la misma carpeta del script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_JSON = os.path.join(BASE_DIR, 'reglas_idioma.json')
if not os.path.exists(RUTA_JSON):
    RUTA_JSON = os.path.join(BASE_DIR, 'reglas_idiomas.json')

def cargar_contexto():
    try:
        with open(RUTA_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Tolerancia a fallos: busca la clave con o sin tilde
        diccionario = data.get('diccionario_básico', data.get('diccionario_basico', {}))

        contexto = (
            f"Eres un traductor estricto al '{data['nombre_idioma']}'.\n"
            f"Reglas e instrucciones:\n"
            f"{chr(10).join('- ' + r for r in data['gramatica'])}\n\n"
            f"Diccionario base (Usar estas sílabas exactas si aplican):\n"
            f"{json.dumps(diccionario, ensure_ascii=False, indent=2)}\n\n"
            f"Instruccion final: Traduce la frase al latín y separa TODAS las palabras en sílabas "
            f"usando guiones (-). Mantén los espacios entre palabras. Devuelve SOLO el resultado."
        )
        return contexto, data['nombre_idioma']
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo JSON en la ruta: {RUTA_JSON}")
        exit()

contexto_instruccion, nombre_idioma = cargar_contexto()

def obtener_latin_silabado_ia(texto_espanol):
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=texto_espanol,
            config=types.GenerateContentConfig(
                system_instruction=contexto_instruccion,
                temperature=0.1,
            ),
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error de API: {e}")
        return ""
    
# --- 2. ALGORITMOS PROPIOS DE ALTERACIÓN (LOGARITMOS YODEN) ---

def ciclo_vocales(vocal, num_silabas, valor):
    """
    Rota una vocal dentro del ciclo [a, e, i, o, u].
    - valor='propio': rotación izquierda a derecha (a -> e -> i -> o -> u)
    - valor='común': rotación derecha a izquierda (u -> o -> i -> e -> a)
    """
    ciclo = ['a', 'e', 'i', 'o', 'u']
    
    if vocal.lower() not in ciclo:
        return vocal
    
    idx = ciclo.index(vocal.lower())
    
    # Reducción matemática base 5 modular
    rotacion = num_silabas % 5
    
    if valor == "propio":
        # Rotación izquierda a derecha
        nueva_idx = (idx + rotacion) % 5
    else:  # valor == "común"
        # Rotación derecha a izquierda
        nueva_idx = (idx - rotacion) % 5
    
    nueva_vocal = ciclo[nueva_idx]
    
    # Mantener mayúsculas
    if vocal.isupper():
        nueva_vocal = nueva_vocal.upper()
    
    return nueva_vocal

    

def cambiar_vocales(silaba, num_silabas_palabra, valor="común"):
    """
    Cambia las vocales de una sílaba usando el ciclo compacto.
    
    Args:
        silaba: la sílaba a procesar
        num_silabas_palabra: cantidad de sílabas en la palabra
        valor: "propio" (rotación a->e->i->o->u) o "común" (rotación u->o->i->e->a)
    """
    vocales = "aeiouAEIOU"
    nueva_silaba = ""

    for letra in silaba:
        if letra in vocales:
            nueva_silaba += ciclo_vocales(letra, num_silabas_palabra, valor)
        else:
            nueva_silaba += letra
    
    return nueva_silaba

def intercambiar_silabas_en_parejas(silabas):
    """Recibe una lista de sílabas y las intercambia en parejas."""
    silabas_alteradas = silabas.copy()
    for i in range(0, len(silabas_alteradas) - 1, 2):
        temp = silabas_alteradas[i]
        silabas_alteradas[i] = silabas_alteradas[i + 1]
        silabas_alteradas[i + 1] = temp
    return silabas_alteradas

def procesar_algoritmos_yoden(texto_latin_silabas):
    """Toma el string 'ca-nem do-mus' y aplica toda tu lógica de ingeniería"""
    palabras_procesadas = []
    palabras_latin = texto_latin_silabas.split()

    for palabra in palabras_latin:
        # Detectar si la palabra tiene comillas para determinar el tipo de rotación
        tiene_comillas = '"' in palabra
        valor = "propio" if tiene_comillas else "común"
        
        # Limpiar comillas
        palabra_limpia = palabra.replace('"', '')
        
        # Limpiar signos de puntuación de forma segura usando el extremo final [-1]
        signo_final = ""
        if palabra_limpia and not palabra_limpia[-1].isalnum() and palabra_limpia[-1] != "-":
            signo_final = palabra_limpia[-1]
            palabra_limpia = palabra_limpia[:-1]

        # Conteo de sílabas
        silabas = palabra_limpia.split('-')
        num_silabas = len(silabas)

        # Cambio de vocales según la cantidad de sílabas
        silabas_con_vocales_cambiadas = []
        for s in silabas:
            s_modificada = cambiar_vocales(s, num_silabas, valor)
            silabas_con_vocales_cambiadas.append(s_modificada)

        # Intercambio de sílabas en parejas
        silabas_intercambiadas = intercambiar_silabas_en_parejas(silabas_con_vocales_cambiadas)

        # Reconstruir la palabra final y re-inyectar su signo de puntuación si tenía
        palabra_final = "".join(silabas_intercambiadas) + signo_final
        palabras_procesadas.append(palabra_final)

    return " ".join(palabras_procesadas)

# --- 3. INTERFAZ EN CONSOLA ---
print(f" === Motor de traducción: Español -> {nombre_idioma} ===")
print("Escribe tu frase en español y presiona Enter. Para salir escribe 'salir'.\n")

while True:
    entrada = input("Español > ")
    if entrada.lower() == 'salir':
        print("¡Hasta luego!")
        break

    if entrada.strip() == "":
        continue

    # Fase 1: API (Traducción al latín y separación silábica pura)
    latin_base_silabado = obtener_latin_silabado_ia(entrada)
    print(f"Base Latín (API) > {latin_base_silabado}")

    # Fase 2: Tus algoritmos (Mutación a Yoden)
    resultado_final = procesar_algoritmos_yoden(latin_base_silabado)
    print(f"Resultado Yoden > {resultado_final}\n")