from flask import Flask, render_template, request, jsonify
import networkx as nx

app = Flask(__name__)

@app.route('/')
def ana_sayfa():
    # Sitenin ilk açılışta görüneceği HTML sayfasını yükler
    return render_template('index.html')

@app.route('/hesapla', methods=['POST'])
def hesapla():
    veri = request.json
    borclar = veri.get('borclar', [])
    
    # Graf yapısını kuruyoruz
    G = nx.DiGraph()
    for b in borclar:
        # Borçlu, Alacaklı ve Miktar verilerini ekliyoruz
        G.add_edge(b['borclu'], b['alacakli'], weight=float(b['miktar']))
    
    # Döngüleri buluyoruz
    donguler = list(nx.simple_cycles(G))
    
    sonuc_metni = ""
    if len(donguler) == 0:
        sonuc_metni = "Harika! Sistemde birbirini kilitleyen herhangi bir borç döngüsü bulunamadı."
    else:
        sonuc_metni = "⚠️ Tıkanıklık Tespit Edildi! Aşağıdaki esnaflar birbirine mahsup edilebilir:\n\n"
        for i, dongu in enumerate(donguler):
            # Döngüyü görsel olarak oklarla bağlıyoruz (Esnaf1 -> Esnaf2 -> Esnaf1)
            zincir = " -> ".join(dongu) + " -> " + dongu[0]
            sonuc_metni += f"{i+1}. Zincir: {zincir}\n"
            sonuc_metni += "💡 Tavsiye: Bu döngüdeki esnaflar ortak miktarda mahsup edilerek piyasadan borç silinebilir!\n"

    return jsonify({"sonuc": sonuc_metni})

if __name__ == '__main__':
    app.run(debug=True)
