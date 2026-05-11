# Examples for Map to GeoJSON Converter

This folder contains sample inputs and outputs to demonstrate what the tool can do.

---

## 📊 What This Tool Does

The Map to GeoJSON Converter takes map images like this:

### Input: Map Image with Regions
![Input Map](https://raw.githubusercontent.com/ironn0/ironn0/main/assets/Map_to_Geojson/italy_input.png)

And converts them to GeoJSON format, extracting polygons for each region:

### Output: Extracted Regions as GeoJSON
![Output GeoJSON](https://raw.githubusercontent.com/ironn0/ironn0/main/assets/Map_to_Geojson/italy_output.png)

The tool automatically:
- Detects colored regions in the map
- Extracts boundaries as polygons
- Identifies centroids for each region
- Exports as standard GeoJSON format

---

## Sample Files
- `italy_input.png`: Sample map image of Italy with regions (input example).
- `italy_output.png`: Visualization showing detected regions with labels (output example).
- `sample_output.geojson`: Expected GeoJSON output from the sample image.
- `sample_svg.svg`: An SVG map file (use for SVG-to-GeoJSON conversion).

## How to Use
1. Place your map image in this folder (or any location).
2. Run the conversion script:
   ```bash
   python "src/tests/test SAM/map_to_geojson.py"
   ```
3. Enter the path to your image when prompted.
4. Choose calibration method (Italy preset recommended for Italian maps).
5. Check outputs:
   - `*_segmented.png`: Color segmentation visualization
   - `*_regions.png`: Detected polygons with centroids
   - `*.geojson`: GeoJSON file ready to use

6. Visualize the GeoJSON at https://geojson.io

---

## Expected Results

The converter will:
- Identify distinct regions based on colors
- Filter out water bodies and background
- Generate clean polygon boundaries
- Assign properties (id, color, area) to each region

Perfect for students who need free geospatial data from map images!

---

## 🆕 Georeferencer (Work in Progress)

A new approach using **Point-in-Polygon** instead of shape matching:

![Georeferencer Output](https://raw.githubusercontent.com/ironn0/ironn0/main/assets/Map_to_Geojson/georeferencer_italy.png)

### Why It's Better
- Uses real geographic coordinates instead of shape comparison
- User selects the map area visually on a world map
- Checkboxes to filter out unwanted regions (sea, background)

### Why It's Not Finished
- Calibration needs fine-tuning for perfect alignment
- Only Italy GADM database included so far
- Edge regions may fall outside expected boundaries

---

## 🌍 Web App - African Kingdoms Example

The latest version includes a **web-based interface** with significant improvements in region detection and georeferencing accuracy.

### Input: Historical Map of African Kingdoms
![Raw Map Input](https://raw.githubusercontent.com/ironn0/ironn0/main/assets/Map_to_Geojson/img_raw_webapp.png)

A historical map showing various African kingdoms (Dendi, Hausa, Bornu, Oyo, Benin) was processed through the webapp.

### Output: Georeferenced GeoJSON on Real Map
![GeoJSON Result](https://raw.githubusercontent.com/ironn0/ironn0/main/assets/Map_to_Geojson/img_result_geojson.png)

The extracted regions are now properly georeferenced and placed on real-world coordinates!

### What's Improved
- **Better edge detection**: Cleaner polygon boundaries with less noise
- **Interactive georeferencing**: Drag corners to align the map precisely
- **Real-time preview**: See your regions on an actual map before exporting
- **Multiple region support**: Handles complex maps with many overlapping territories
- **Web interface**: No installation required, works directly in browser