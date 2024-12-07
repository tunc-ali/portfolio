const API_URL = "https://api.antwerpen.be/v1/parkings"; // API URL'si
const API_KEY = "SENİN_API_ANAHTARIN"; // API Anahtarı

async function fetchParkingData() {
    try {
        const response = await fetch(API_URL, {
            headers: {
                "Authorization": `Bearer ${API_KEY}`,
                "Content-Type": "application/json"
            }
        });

        if (!response.ok) throw new Error("API çağrısı başarısız oldu!");

        const data = await response.json();
        initializeMap(data); // Veriyi haritaya aktar
    } catch (error) {
        console.error("API Hatası:", error);
    }
}

function initializeMap(parkingData) {
    // Haritayı oluştur
    const map = L.map('map').setView([51.2194475, 4.4024643], 12); // Antwerp koordinatları
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    // API'den gelen park yerlerini işaretle
    parkingData.forEach((parking) => {
        L.marker([parking.latitude, parking.longitude])
            .addTo(map)
            .bindPopup(`<strong>${parking.name}</strong><br>Adres: ${parking.address}`)
            .openPopup();
    });
}

// Sayfa yüklendiğinde API'yi çağır
document.addEventListener("DOMContentLoaded", fetchParkingData);
