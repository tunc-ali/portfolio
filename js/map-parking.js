// /* In dit script plaats je de code om de kaart te tonen in de aside van de contactpagina. De coördinaten van de parking in Gent zijn: 51.0424221 en 3.7258331.
// De initiële grootte is 15 met een maximale zoom van 19.
// Gebruik hiervoor de documentatie op https://leafletjs.com/ 
// */


let map = L.map('map').setView([51.0424221, 3.7258331], 15);

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

L.marker([51.0424221, 3.7258331]).addTo(map)
    .bindPopup('Gent Parking')
    .openPopup();

let markerIconP1 = L.icon({
    iconUrl: 'assets/images/icon.png',
    iconSize: [60, 60],               
    iconAnchor: [30, 60],            
    popupAnchor: [0, -60]            
});


L.marker([51.0424221, 3.7258331], { icon: markerIconP1 })
    .addTo(map)
    .bindPopup('Dit is een voorbeeld van een marker met een aangepaste icon.')
    .openPopup();

let baseMaps = {
    "OpenStreetMap": L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png'),
    "CartoDB": L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        subdomains: 'abcd',
    }),
    "Stamen Toner": L.tileLayer('https://stamen-tiles.a.ssl.fastly.net/toner/{z}/{x}/{y}.png')
};

L.control.layers(baseMaps).addTo(map);
