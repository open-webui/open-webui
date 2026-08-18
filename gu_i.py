import urllib.request
import urllib.parse
import os

text = "હાલમાં એચએલટી (Wet Well Level) સ્તર 3802.84 mm છે. આ સ્તર મોડરેટ (Moderate) કેટેગરીમાં આવે છે, જે સૂચવે છે કે ટાંકીનું સ્તર સામાન્ય કરતા થોડું વધારે છે."

textUrl = urllib.parse.quote(text)
url = f"https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=gu&q={textUrl}"

print(f"Downloading from: {url}")

req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response, open('test_gujarati.mp3', 'wb') as out_file:
        out_file.write(response.read())
    print(f"Saved to test_gujarati.mp3. Size: {os.path.getsize('test_gujarati.mp3')} bytes")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print(e.read().decode('utf-8', errors='ignore'))
except Exception as e:
    print(f"Error: {e}")
