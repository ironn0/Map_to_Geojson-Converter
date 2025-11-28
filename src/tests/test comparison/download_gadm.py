"""
Download GADM Italy Regions - Database regioni italiane ufficiali
Livello ADM1 = Regioni (non province)
"""

import urllib.request
import zipfile
from pathlib import Path
import geopandas as gpd


def download_gadm_italy():
    """Scarica database regioni Italia da GADM"""
    print("\n📥 Download GADM Italy - Regioni Ufficiali")
    print("="*60)
    
    base_dir = Path(__file__).parent / "geodata"
    base_dir.mkdir(exist_ok=True)
    
    gadm_dir = base_dir / "gadm_italy"
    gadm_dir.mkdir(exist_ok=True)
    
    # GADM Italy Level 1 (Regioni) - URL aggiornato per GADM 4.1
    url = "https://geodata.ucdavis.edu/gadm/gadm4.1/shp/gadm41_ITA_shp.zip"
    zip_path = gadm_dir / "gadm_italy.zip"
    shapefile = gadm_dir / "gadm41_ITA_1.shp"
    
    if shapefile.exists():
        print(f"✅ Database già presente: {shapefile}")
        
        # Mostra regioni
        gdf = gpd.read_file(str(shapefile))
        print(f"\n📊 {len(gdf)} regioni italiane:")
        for name in sorted(gdf['NAME_1'].unique()):
            print(f"   • {name}")
        
        return shapefile
    
    try:
        print(f"   URL: {url}")
        print(f"   Download in corso...")
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            chunk_size = 8192
            
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)
                
                if total_size > 0:
                    progress = (downloaded / total_size) * 100
                    print(f"\r   Progresso: {progress:.1f}%", end='', flush=True)
        
        print("\n   Estrazione...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(gadm_dir)
        
        zip_path.unlink()
        
        print(f"   ✅ Download completato!")
        
        # Mostra regioni
        gdf = gpd.read_file(str(shapefile))
        print(f"\n📊 {len(gdf)} regioni italiane:")
        for name in sorted(gdf['NAME_1'].unique()):
            print(f"   • {name}")
        
        return shapefile
        
    except Exception as e:
        print(f"\n   ❌ Errore: {e}")
        print("\n   💡 ALTERNATIVA MANUALE:")
        print("   1. Vai su: https://gadm.org/download_country.html")
        print("   2. Seleziona: Italy")
        print("   3. Scarica: Shapefile (Level 1)")
        print(f"   4. Estrai in: {gadm_dir}")
        raise


if __name__ == "__main__":
    download_gadm_italy()
