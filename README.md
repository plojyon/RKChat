# RKChat

Pogovorna aplikacija za RK.

## Zagon programa
Odjemalec: `python3 chatClient.py` ali `python3 chatClient.py ip:port`  
Strežnik: `python3 chatServer.py` ali `python3 chatServer.py ip:port`  

Za testiranje so priloženi uporabniški certifikati `certs/asistent`, `certs/yon`, `certs/masa` in `certs/mallory`. Slednji ni registriran na strežniku.

## Navodilo za generiranje uporabniškega certifikata
1. Uporabite ukaz `openssl req -new -newkey rsa:2048 -days 365 -nodes -sha256 -x509 -keyout uporabnik.key -out uporabnik.crt`.

2. Sledite navodilom v ukaznem pozivu. V polje Common Name vnesite željeno uporabniško ime. Dovoljene so male in velike črke angleške abecede in znaka "_" ter "-".

3. Vsebino datoteke `uporabnik.crt` mora strežniški administrator ročno dodati v `clients.pem`.

## Navodila za uporabo
1. Pridružite se aplikaciji za klepet tako, da vnesete pot do certifikata brez končnice (npr. `certs/asistent` ali `uporabnik`).

2. Vnesite svoje sporočilo v besedilno polje, da začnete klepetati z drugimi.

3. Pritisnite tipko Enter, da pošljete svoje sporočilo.

4. Če želite poslati zasebno sporočilo, ga začnite z znakom "@" in uporabniškim imenom prejemnika, npr. `@yon pozdravljen!`

5. Videli boste vsa sporočila drugih uporabnikov v klepetalnici na konzoli.

6. Za izhod iz aplikacije hkrati pritisnite tipki "Ctrl" in "C".
