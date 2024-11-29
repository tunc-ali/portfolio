// maak connectie met parking-API van de stad Gent
fetch('https://data.stad.gent/api/explore/v2.1/catalog/datasets/bezetting-parkeergarages-real-time/records?limit=1&refine=name%3ASint-Pietersplein')
    .then(function (response) {
        // nakijken of de API-call een antwoord terugstuurt
        if (response.ok) {
            // als de status "ok" (=200) is, dan wordt het antwoord omgezet in JSON
            return response.json();
        } else {
            // als de status niet "ok" is, geef dan de status terug en annuleer het uitvoeren
            return Promise.reject(response.status);
        }
    })
    .then(function (response) {
        console.log(response);
        let html = '<section class="accordion" id="accordionExample">';

        // Gegevens van de parking in HTML
        response.records.forEach((record, i) => {
            const parking = record.record.fields;
            html += `
            <div class="accordion-item">
                <h2 class="accordion-header">
                    <button class="accordion-button collapsed text-uppercase fs-6 fw-bolder pt-3" type="button" data-bs-toggle="collapse" data-bs-target="#collapse${i}" aria-expanded="false" aria-controls="collapse${i}">
                        ${parking.name}
                    </button>
                </h2>
                <div id="collapse${i}" class="accordion-collapse collapse" aria-labelledby="heading${i}" data-bs-parent="#accordionExample">
                    <div class="accordion-body">
                        <p><b>Beschikbare capaciteit:</b> ${parking.availablecapacity}</p>
                        <p><b>Totale capaciteit:</b> ${parking.totalcapacity}</p>
                    </div>
                </div>
            </div>`;
        });

        html += '</section>';
        document.getElementById("parkingGent").innerHTML = html;
    })
    .catch(function (error) {
        // indien er een fout is, toon in de console dan wat er misloopt
        console.error("Error with message: " + error);
    });
