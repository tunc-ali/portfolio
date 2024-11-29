// toon het huidige jaar in de footer
// haal eerste het huidige jaar op
const currentYear = new Date().getFullYear();
// toon huidige jaar nadien in het element met id "year" in footer
document.getElementById("year").textContent = currentYear;