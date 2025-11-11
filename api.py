"""
============================================
BACKEND API COMPLETO
Sistema de Storage para conectar Bot de WhatsApp con Catálogo Web
============================================
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import sqlite3

app = Flask(__name__)
CORS(app)  # Permitir peticiones desde cualquier dominio

# ============================================
# CONFIGURACIÓN DE BASE DE DATOS
# ============================================

DB_NAME = 'catalogo.db'

def init_db():
    """Inicializar base de datos SQLite"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabla de productos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            descripcion TEXT,
            tallas TEXT,
            imagen TEXT,
            fecha TEXT NOT NULL
        )
    ''')
    
    # Tabla de configuración (última actualización, etc.)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracion (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            fecha TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Base de datos inicializada")

# Inicializar BD al arrancar
init_db()

# ============================================
# ENDPOINTS DE STORAGE
# ============================================

@app.route('/storage/set', methods=['POST'])
def storage_set():
    """Guardar o actualizar un valor en el storage"""
    try:
        data = request.get_json()
        key = data.get('key')
        value = data.get('value')
        shared = data.get('shared', True)
        
        if not key or not value:
            return jsonify({'error': 'key y value son requeridos'}), 400
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Si la key es de producto
        if key.startswith('zapato:'):
            producto = json.loads(value)
            cursor.execute('''
                INSERT OR REPLACE INTO productos 
                (id, nombre, precio, descripcion, tallas, imagen, fecha)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                producto['id'],
                producto['nombre'],
                producto['precio'],
                producto.get('descripcion', ''),
                producto.get('tallas', ''),
                producto.get('imagen', ''),
                producto['fecha']
            ))
        else:
            # Configuración u otros datos
            cursor.execute('''
                INSERT OR REPLACE INTO configuracion (key, value, fecha)
                VALUES (?, ?, ?)
            ''', (key, value, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Guardado: {key}")
        return jsonify({'success': True, 'key': key}), 200
        
    except Exception as e:
        print(f"❌ Error en storage_set: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/storage/get', methods=['GET'])
def storage_get():
    """Obtener un valor del storage"""
    try:
        key = request.args.get('key')
        shared = request.args.get('shared', 'true').lower() == 'true'
        
        if not key:
            return jsonify({'error': 'key es requerido'}), 400
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Si es un producto específico
        if key.startswith('zapato:'):
            cursor.execute('SELECT * FROM productos WHERE id = ?', (key,))
            row = cursor.fetchone()
            
            if row:
                producto = {
                    'id': row[0],
                    'nombre': row[1],
                    'precio': row[2],
                    'descripcion': row[3],
                    'tallas': row[4],
                    'imagen': row[5],
                    'fecha': row[6]
                }
                conn.close()
                return jsonify({'key': key, 'value': json.dumps(producto)}), 200
            else:
                conn.close()
                return jsonify({'error': 'No encontrado'}), 404
        else:
            # Configuración
            cursor.execute('SELECT value FROM configuracion WHERE key = ?', (key,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return jsonify({'key': key, 'value': row[0]}), 200
            else:
                return jsonify({'error': 'No encontrado'}), 404
                
    except Exception as e:
        print(f"❌ Error en storage_get: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/storage/list', methods=['GET'])
def storage_list():
    """Listar todas las keys que coincidan con un prefijo"""
    try:
        prefix = request.args.get('prefix', '')
        shared = request.args.get('shared', 'true').lower() == 'true'
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        if prefix.startswith('zapato:'):
            # Listar todos los productos
            cursor.execute('SELECT * FROM productos ORDER BY fecha DESC')
            rows = cursor.fetchall()
            
            productos = []
            for row in rows:
                productos.append({
                    'id': row[0],
                    'nombre': row[1],
                    'precio': row[2],
                    'descripcion': row[3],
                    'tallas': row[4],
                    'imagen': row[5],
                    'fecha': row[6]
                })
            
            conn.close()
            return jsonify({
                'keys': [p['id'] for p in productos],
                'productos': productos,  # Enviar productos completos
                'count': len(productos)
            }), 200
        else:
            conn.close()
            return jsonify({'keys': [], 'count': 0}), 200
            
    except Exception as e:
        print(f"❌ Error en storage_list: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/storage/delete', methods=['DELETE'])
def storage_delete():
    """Eliminar un valor del storage"""
    try:
        key = request.args.get('key')
        shared = request.args.get('shared', 'true').lower() == 'true'
        
        if not key:
            return jsonify({'error': 'key es requerido'}), 400
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        if key.startswith('zapato:'):
            cursor.execute('DELETE FROM productos WHERE id = ?', (key,))
        else:
            cursor.execute('DELETE FROM configuracion WHERE key = ?', (key,))
        
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        if affected > 0:
            print(f"🗑️ Eliminado: {key}")
            return jsonify({'success': True, 'deleted': True, 'key': key}), 200
        else:
            return jsonify({'error': 'No encontrado'}), 404
            
    except Exception as e:
        print(f"❌ Error en storage_delete: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================
# ENDPOINTS ADICIONALES ÚTILES
# ============================================

@app.route('/api/productos', methods=['GET'])
def get_productos():
    """Endpoint simplificado para obtener todos los productos (para el catálogo web)"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM productos ORDER BY fecha DESC')
        rows = cursor.fetchall()
        
        productos = []
        for row in rows:
            productos.append({
                'id': row[0],
                'nombre': row[1],
                'precio': row[2],
                'descripcion': row[3],
                'tallas': row[4],
                'imagen': row[5],
                'fecha': row[6]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'productos': productos,
            'count': len(productos)
        }), 200
        
    except Exception as e:
        print(f"❌ Error en get_productos: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Obtener estadísticas del catálogo"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Total de productos
        cursor.execute('SELECT COUNT(*) FROM productos')
        total = cursor.fetchone()[0]
        
        # Última actualización
        cursor.execute('SELECT value FROM configuracion WHERE key = ?', 
                      ('catalog:ultima_actualizacion',))
        ultima_act = cursor.fetchone()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total_productos': total,
            'ultima_actualizacion': json.loads(ultima_act[0]) if ultima_act else None
        }), 200
        
    except Exception as e:
        print(f"❌ Error en get_stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    """Página de inicio con documentación"""
    return """
    <html>
    <head>
        <title>API de Catálogo de Zapatos</title>
        <style>
            body { font-family: Arial; max-width: 900px; margin: 50px auto; padding: 20px; }
            h1 { color: #25D366; }
            .endpoint { background: #f5f5f5; padding: 15px; margin: 15px 0; border-radius: 8px; }
            code { background: #e0e0e0; padding: 2px 6px; border-radius: 4px; }
            .method { display: inline-block; padding: 4px 10px; border-radius: 4px; font-weight: bold; }
            .post { background: #49cc90; color: white; }
            .get { background: #61affe; color: white; }
            .delete { background: #f93e3e; color: white; }
        </style>
    </head>
    <body>
        <h1>🛒 API de Catálogo de Zapatos</h1>
        <p><strong>Status:</strong> ✅ Funcionando</p>
        
        <h2>📡 Endpoints disponibles</h2>
        
        <div class="endpoint">
            <span class="method get">GET</span>
            <code>/api/productos</code>
            <p>Obtener todos los productos (para el catálogo web)</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span>
            <code>/api/stats</code>
            <p>Obtener estadísticas del catálogo</p>
        </div>
        
        <div class="endpoint">
            <span class="method post">POST</span>
            <code>/storage/set</code>
            <p>Guardar producto (usado por el bot de WhatsApp)</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span>
            <code>/storage/get?key=zapato:123</code>
            <p>Obtener un producto específico</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span>
            <code>/storage/list?prefix=zapato:</code>
            <p>Listar todos los productos</p>
        </div>
        
        <div class="endpoint">
            <span class="method delete">DELETE</span>
            <code>/storage/delete?key=zapato:123</code>
            <p>Eliminar un producto</p>
        </div>
        
        <h2>🔗 Integración</h2>
        <p><strong>Bot de WhatsApp:</strong> Usa estos endpoints para guardar productos</p>
        <p><strong>Catálogo Web:</strong> Usa <code>/api/productos</code> para mostrar productos</p>
    </body>
    </html>
    """

@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'database': 'connected'
    }), 200

# ============================================
# INICIAR SERVIDOR
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"""
    ============================================
    🚀 API Backend iniciada
    ============================================
    🗄️  Base de datos: SQLite ({DB_NAME})
    🌐 Puerto: {port}
    📡 Endpoints:
       - GET  /api/productos (catálogo web)
       - POST /storage/set (bot WhatsApp)
       - GET  /storage/list (listar productos)
    ============================================
    """)
    app.run(host='0.0.0.0', port=port, debug=True)