import google.generativeai as genai
from PIL import Image
from io import BytesIO
import base64
from dotenv import load_dotenv
import os

def generate_image(prompt, output_filename='gemini-generated-image.png'):
    """
    Genera un'immagine basata sul prompt fornito.
    
    Args:
        prompt (str): Il testo descrittivo dell'immagine da generare
        output_filename (str): Il nome del file in cui salvare l'immagine generata
    
    Returns:
        str: Il percorso del file immagine generato, o None se la generazione fallisce
    """
    # Carica le variabili d'ambiente dal file .env
    load_dotenv()

    # API key
    api_key = "AIzaSyC1bXxZ4447S7p3RfupwWPjLVEIuLR3Vtg"

    # Configura l'API key
    genai.configure(api_key=api_key)

    try:
        # Ottieni il modello Gemini
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Genera il contenuto
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.9,
            }
        )
        
        # Controlla se la risposta contiene parti
        if hasattr(response.candidates[0].content, 'parts'):
            parts = response.candidates[0].content.parts
            
            # Cerca un'immagine nelle parti
            for part in parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    image_data = base64.b64decode(part.inline_data.data)
                    image = Image.open(BytesIO(image_data))
                    image.save(output_filename)
                    print(f"Immagine salvata come '{output_filename}'")
                    return output_filename
                
            print("Nessuna immagine trovata nella risposta.")
            return None
            
        else:
            print("Risposta senza parti separate.")
            return None
            
    except Exception as e:
        print(f"Si è verificato un errore durante la generazione dell'immagine: {str(e)}")
        return None

# Esempio di utilizzo
if __name__ == "__main__":
    test_prompt = ('Create a 3D rendered image of a pig with wings and a top hat flying over a happy '
                  'futuristic scifi city with lots of greenery.')
    generate_image(test_prompt)