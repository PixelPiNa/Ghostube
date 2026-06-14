function regresarAlInicio() {
    // Leemos la última ruta guardada
    const ultimaRuta = sessionStorage.getItem('ultima_ruta_inicio');
    
    if (ultimaRuta) {
        window.location.href = ultimaRuta; // Regresa exactamente a donde estaba (con todo y búsquedas)
    } else {
        window.location.href = '/'; // Fallback de seguridad al inicio general
    }
}