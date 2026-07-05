import React, { useState } from 'react';

function App() {
  const [busqueda, setBusqueda] = useState('');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Función que se ejecuta al enviar el formulario
  const buscarCliente = (e) => {
    e.preventDefault(); // Evita que la página se recargue
    if (!busqueda.trim()) return;

    setLoading(true);
    setError(null);
    setData(null);

    // Inyectamos lo que el usuario escribió en la URL
    fetch(`https://proyectowebcolaboradores.onrender.com/api/v1/clientes/${busqueda}/riesgo/`)
      .then((response) => {
        if (!response.ok) throw new Error('Cliente no encontrado en la base de datos');
        return response.json();
      })
      .then((datos) => {
        setData(datos);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  };

  return (
    <div style={{
      backgroundColor: '#F0F4F8',
      minHeight: '100vh',
      fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      padding: '20px'
    }}>
      
      {/* Barra de Búsqueda */}
      <form onSubmit={buscarCliente} style={{ marginBottom: '24px', display: 'flex', gap: '10px', width: '100%', maxWidth: '500px' }}>
        <input 
          type="text" 
          placeholder="Ingrese el ID o Cédula del cliente..." 
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          style={{
            flex: 1,
            padding: '12px 16px',
            borderRadius: '8px',
            border: '1px solid #CBD5E1',
            fontSize: '1rem',
            outline: 'none'
          }}
        />
        <button type="submit" style={{
          backgroundColor: '#0B132B',
          color: '#FFFFFF',
          border: 'none',
          padding: '12px 24px',
          borderRadius: '8px',
          fontSize: '1rem',
          fontWeight: 'bold',
          cursor: 'pointer'
        }}>
          Buscar
        </button>
      </form>

      {/* Estados de Carga y Error */}
      {loading && <div style={{ padding: '20px', color: '#64748B' }}>Consultando Motor CBR...</div>}
      {error && <div style={{ padding: '20px', color: '#B91C1C', backgroundColor: '#FEE2E2', borderRadius: '8px', width: '100%', maxWidth: '500px', textAlign: 'center' }}>⚠️ {error}</div>}

      {/* Tarjeta de Resultados (Solo se muestra si hay data) */}
      {data && (
        <div style={{
          backgroundColor: '#FFFFFF',
          borderRadius: '12px',
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
          maxWidth: '500px',
          width: '100%',
          overflow: 'hidden',
          border: '1px solid #E2E8F0'
        }}>
          <div style={{ backgroundColor: '#0B132B', padding: '20px', color: '#FFFFFF' }}>
            <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Dashboard Externo: Motor CBR</h2>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: '#CBD5E1' }}>Consulta de Microservicios en Tiempo Real</p>
          </div>

          <div style={{ padding: '24px' }}>
            <h3 style={{ color: '#0F172A', margin: '0 0 15px 0' }}>{data.nombres}</h3>
            
            <div style={{ marginBottom: '12px', fontSize: '0.95rem' }}>
              <span style={{ color: '#64748B', fontWeight: '500' }}>Identificador:</span> 
              <strong style={{ color: '#334155', marginLeft: '8px' }}>{data.cliente_id}</strong>
            </div>

            <div style={{ marginBottom: '20px', fontSize: '0.95rem' }}>
              <span style={{ color: '#64748B', fontWeight: '500' }}>Categoría de Riesgo:</span> 
              <span style={{
                marginLeft: '8px',
                backgroundColor: '#FAFAFA',
                padding: '4px 10px',
                borderRadius: '6px',
                border: '1px solid #E2E8F0',
                fontWeight: 'bold',
                color: '#1E3A8A'
              }}>{data.categoria_riesgo}</span>
            </div>

            <div style={{
              backgroundColor: '#0B132B',
              color: '#FFFFFF',
              padding: '20px',
              borderRadius: '8px',
              borderLeft: '4px solid #D4AF37'
            }}>
              <h4 style={{ margin: '0 0 10px 0', color: '#D4AF37', fontSize: '1rem' }}>🧠 Sugerencia del Motor CBR</h4>
              <p style={{ margin: '0 0 12px 0', fontSize: '1.1rem', fontWeight: '600' }}>{data.recomendacion_cbr.tecnica}</p>
              
              <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '10px', fontSize: '0.85rem' }}>
                <span style={{ color: '#CBD5E1' }}>Confianza del Algoritmo:</span>
                <strong style={{ color: '#D4AF37', marginLeft: '6px', fontSize: '1rem' }}>{data.recomendacion_cbr.similitud_confianza}%</strong>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;