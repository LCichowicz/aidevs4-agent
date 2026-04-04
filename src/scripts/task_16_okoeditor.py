import json
from src.config import AI_DEVS_API
from src.llm.hub_client import HubClient


HUB_URL = "https://hub.ag3nts.org/api/"

task = 'okoeditor'
# answer = {
#     "action": "help"
#     }

# answer = {"page": "zadania",
#           "id": "380792b2c86d9c5be670b3bde48e187b",
#           "action": "update",
#           "content": '''Czujniki zarejestrowały szybko poruszający się obiekt zmierzający w kierunku rzeki. Ruch był nieregularny i momentami osiągał wysokie prędkości, co początkowo mogło sugerować zakłócenie pomiaru.
#                         Po stabilizacji sygnału ustalono, że obiekt rzeczywiście znajdował się nad terenem w pobliżu Skolwina. Charakterystyka ruchu - zmienna prędkość, nagłe zmiany kierunku oraz spowolnienie tuż przy rzece - wskazuje na aktywność zwierząt, najprawdopodobniej dużych ssaków wodnych lub ptactwa.
#                         Końcowa faza obserwacji sugeruje zejście obiektu nisko nad teren lub wejście do środowiska wodnego, co jest spójne z zachowaniem zwierząt w tym rejonie.
#                         Nie stwierdzono żadnych oznak obecności ludzi ani pojazdów. Zdarzenie zostało zaklasyfikowane jako naturalna aktywność fauny i nie wymaga dalszych działań operacyjnych.''',
#           'title': "Nietypowa aktywność zwierząt w rejonie Skolwina",
#           "done": "YES"}

# answer = {
#   "action": "update",
#   "page": "incydenty",
#   "id": "380792b2c86d9c5be670b3bde48e187b",
#   "title": "MOVE04 Aktywność zwierząt w rejonie Skolwina",
#   "content": '''Czujniki zarejestrowały szybko poruszający się obiekt zmierzający w kierunku rzeki. Ruch był nieregularny i momentami osiągał wysokie prędkości, co początkowo mogło sugerować zakłócenie pomiaru.
#                         Po stabilizacji sygnału ustalono, że obiekt rzeczywiście znajdował się nad terenem w pobliżu Skolwina. Charakterystyka ruchu - zmienna prędkość, nagłe zmiany kierunku oraz spowolnienie tuż przy rzece - wskazuje na aktywność zwierząt, najprawdopodobniej dużych ssaków wodnych lub ptactwa.
#                         Końcowa faza obserwacji sugeruje zejście obiektu nisko nad teren lub wejście do środowiska wodnego, co jest spójne z zachowaniem zwierząt w tym rejonie.
#                         Nie stwierdzono żadnych oznak obecności ludzi ani pojazdów. Zdarzenie zostało zaklasyfikowane jako naturalna aktywność fauny i nie wymaga dalszych działań operacyjnych.''',
# }

# answer= {
#   "action": "update",
#   "page": "incydenty",
#   "id": "8b04cb375286948cbe22b446b81921ba",
#   "title": "MOVE01 Wykrycie ruchu ludzi w rejonie miasta Komarowo",
#   "content": '''Zestawienie najnowszych zdarzeń wykrytych przez system nasłuchu komunikacji radiowej.
# 03.04.2026 04:58 | RADIO | PILNE
# Zarejestrowano powtarzalną emisję głosową w paśmie krótkofalowym na częstotliwości 7.245 MHz. Sygnał pojawiał się cyklicznie w odstępach kilkunastu sekund. Kierunek źródła wskazuje na obszar w pobliżu miasta Komarowo.
# Analiza charakterystyki sygnału sugeruje obecność ludzi prowadzących komunikację głosową w terenie. Nie wykryto ruchu pojazdów ani infrastruktury sieciowej.
# Zdarzenie sklasyfikowano jako aktywność ludzką poza głównymi szlakami komunikacyjnymi.'''
# }

answer = {
    "action": "done"
}


if __name__ == "__main__":
    hub = HubClient()
    payload={
        "apikey": AI_DEVS_API,
        "answer": answer
    }



    


    final_answer = hub.submit(task=task, answer=answer)
    print(json.dumps(final_answer, indent=2))
