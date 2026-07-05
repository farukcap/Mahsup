import os
from flask import Flask, render_template, request, jsonify
import networkx as nx

app = Flask(__name__)

def optimize_debts(borclar):
    """
    Gelişmiş Finansal Optimizasyon Algoritması.
    Tüm borç havuzunu tarar, net alacak/borç dengesini (Arta Kalan Miktar) bulur
    ve minimum işlemle net ödenmesi gereken miktarları hesaplar.
    """
    bakiyeler = {}
    
    # 1. Adım: Herkesin net nakit pozisyonunu hesapla (Alacaklar - Borçlar)
    for b in borclar:
        borclu = b['borclu'].strip().title()
        alacakli = b['alacakli'].strip().title()
        miktar = float(b['miktar'])
        
        bakiyeler[borclu] = bakiyeler.get(borclu, 0.0) - miktar
        bakiyeler[alacakli] = bakiyeler.get(alacakli, 0.0) + miktar
        
    # 2. Adım: Borçluları ve Alacaklıları Ayır
    borclular = []
    alacaklilar = []
    
    for kisi, bakiye in bakiyeler.items():
        if bakiye < -0.01:
            borclular.append({'isim': kisi, 'bakiye': abs(bakiye)})
        elif bakiye > 0.01:
            alacaklilar.append({'isim': kisi, 'bakiye': bakiye})
            
    # 3. Adım: Net Ödeme Planını Çıkar (Greedy Defter Optimizasyonu)
    net_odemeler = []
    i, j = 0, 0
    
    while i < len(borclular) and j < len(alacaklilar):
        b_kisi = borclular[i]
        a_kisi = alacaklilar[j]
        
        odenecek = min(b_kisi['bakiye'], a_kisi['bakiye'])
        
        net_odemeler.append({
            "gonderen": b_kisi['isim'],
            "alan": a_kisi['isim'],
            "miktar": round(odenecek, 2)
        })
        
        b_kisi['bakiye'] -= odenecek
        a_kisi['bakiye'] -= odenecek
        
        if b_kisi['bakiye'] < 0.01: i += 1
        if a_kisi['bakiye'] < 0.01: j += 1

    # 4. Adım: Genel Durum Özeti (Arta Kalan / Net Bakiyeler)
    özet = []
    for kisi, bakiye in bakiyeler.items():
        özet.append({
            "isim": kisi,
            "durum": "Alacaklı (+)" if bakiye > 0 else ("Borçlu (-)" if bakiye < 0 else "Dengede"),
            "bakiye": round(bakiye, 2)
        })
        
    return net_odemeler, özet

@app.route('/')
def ana_sayfa():
    return render_template('index.html')

@app.route('/hesapla', methods=['POST'])
def hesapla():
    try:
        veri = request.json
        borclar = veri.get('borclar', [])
        
        if not borclar:
            return jsonify({"hata": "Veri havuzu boş."}), 400
            
        # 1. Yapılandırılmış Grafik Üzerinden Döngü Analizi
        G = nx.DiGraph()
        for b in borclar:
            G.add_edge(b['borclu'].strip().title(), b['alacakli'].strip().title(), weight=float(b['miktar']))
            
        donguler = list(nx.simple_cycles(G))
        temizlenmiş_donguler = []
        for d in donguler:
            zincir = " ➔ ".join(d) + " ➔ " + d[0]
            temizlenmiş_donguler.append(zincir)
            
        # 2. Gelişmiş Netleştirme Algoritmasını Çalıştır
        net_odemeler, genel_ozet = optimize_debts(borclar)
        
        # Toplam sisteme giren hacim ve temizlenen hacim analizi
        toplam_brut_borc = sum(float(b['miktar']) for b in borclar)
        toplam_net_borc = sum(n['miktar'] for n in net_odemeler)
        silinen_borc_hacmi = toplam_brut_borc - toplam_net_borc
        
        return jsonify({
            "donguler": temizlenmiş_donguler,
            "net_odemeler": net_odemeler,
            "genel_ozet": genel_ozet,
            "analiz": {
                "toplam_brut": round(toplam_brut_borc, 2),
                "toplam_net": round(toplam_net_borc, 2),
                "silinen_hacim": round(silinen_borc_hacmi, 2)
            }
        })
    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
else:
    app = app
