/* In dit script plaats je de code om de kaart in de id apMap te tekenen, zodat de AP-Hogeschool met adres Ellermanstraat 33 gecentreerd staat. De coördinaten van AP zijn: 51.23009 en 4.41616.
De initiële grootte is 16 met een maximale zoom van 19.
Gebruik hiervoor de documentatie op https://leafletjs.com/ 
*/

let map = L.map('apMap').setView([51.23009, 4.41616], 16);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    
}).addTo(map);

// bepaal de rechthoek rondom het gebouw van AP (coördinaten zijn 51.23041, 4.4155 en 51.22991, 4.41675)

let bounds = [[51.23041, 4.4155], [51.22991, 4.41675]]; 

// kleur de rechthoek in met de rode AP-kleur (#e60005)
L.rectangle(bounds, {color: '#e60005', weight: 1}).addTo(map);

map.fitBounds(bounds);
// plaats een marker (coördinaten 51.23009 en 4.41616) met als tekst "AP-Hogeschool" en eronder "Ellermanstraat 33"
let apMarker = L.marker([51.23009, 4.41616]).addTo(map);
apMarker.bindPopup("<b>AP-Hogeschool</b><br>Ellermanstraat 33").openPopup();



