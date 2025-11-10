Feasibility Study - [Image-to-GeoJSON Converter]
=======================================
[TOC]

v0.0.3 - 2025-10-17 - Fabio Ferro

<br>

# Executive Summary

### Project brief description
Development of an application capable of converting images of geographic maps into GeoJSON format using deep learning techniques, leveraging local hardware resources and open-source software, with the goal of automating geospatial data creation at zero cost.

### Main purpose of the study
Assess the technical and organizational feasibility of the project, identifying associated risks and opportunities, considering the zero-cost constraint and the use of local resources.

### Final recommendation
[Feasible with Conditions] - The project is feasible but requires careful planning, use of open-source software, and efficient management of local hardware resources.

### Estimated investment
€0

### Expected ROI
High in terms of time savings and skills to be acquired

### Main risks
* Availability and quality of open-source training data.
* Complexity of implementing the deep learning model with limited hardware resources.
* Long training times.
* Market adoption
* Competition with existing solutions

<br>

# 1. Introduction

### Purpose of this document
Define the feasibility of the "Image-to-GeoJSON Converter (Zero Cost)" project by analyzing technical and organizational aspects, considering the zero-cost constraint and the use of local resources.

### Project context
The project fits within the growing demand for geospatial data and the need to automate the processes of creating it, focusing on the use of open-source resources and local hardware to reduce costs.

### Stakeholders
* Fabio Ferro (Developer)
* Marrocu Mattia (UI Designer)
* Cortinovis Luca (GIS and geospatial data researcher)
* End users (e.g., GIS companies, public bodies)
* Open-source community

<br>

# 2. Project Description

## 2.1 Project Objectives

### Project goals
* Develop an application able to convert images of geographic maps into GeoJSON format using deep learning techniques.
* Automate the creation of geospatial data at zero cost.
* Exploit local hardware resources.
* Use open-source software (PyTorch, OpenCV, GeoPandas, etc.).
* Achieve an acceptable conversion accuracy (to be defined based on available resources).

### Secondary objectives
* Support various open-source geographic map image formats.
* Provide an intuitive user interface (may be simplified to reduce development costs).
* Integrate the application with existing open-source GIS platforms.
* Optimize the deep learning model to run efficiently on local hardware resources.

### Success KPIs
* Conversion accuracy
* Conversion time
* Hardware resource usage
* Application stability and reliability
* Community engagement

<br>

## 2.2 Key Features
### Core functionality
* Upload open-source geographic map images.
* Automatic detection of geographic elements (boundaries, cities, rivers) using an optimized deep learning model.
* Conversion to GeoJSON format.
* Results visualization.
* Manual editing and correction of results (may be simplified).


<br>

## 2.3 Fundamental Requirements

### Technical
* Deep learning libraries: PyTorch (with GPU support).
* Image processing libraries: OpenCV.
* GIS libraries: GeoPandas, Rasterio.
* Programming language: Python.

### Operational
* Process for collecting and preparing open-source training data.
* Data annotation process (may require open-source tools or a simplified in-house tool).
* Training and validation workflow for the deep learning model, optimized for local hardware.
* Model maintenance and update process.
* Technical support for users (primarily via the open-source community).

### Regulatory
* Compliance with open-source licenses for training data and libraries used.
* Compliance with data privacy regulations (if user data collection is planned).

<br>

# 3. Market Analysis

## 3.1 Demand Analysis

### Target customers
* Users needing to convert map images to GeoJSON at zero cost.
* Open-source community.
* Researchers.
* Hobbyists.

### Market size
Difficult to assess due to lack of comparable open-source tools.

### Market trends
* Growth of the open-source geospatial community.
* Development of new deep learning technologies for image analysis.

<br>

## 3.2 Competitor Analysis
| Competitor | Strengths | Weaknesses | Market share |
|------------|-----------|------------|--------------|
| geojson.io | Allows drawing shapes via I/O devices | Does not convert images, only other geospatial formats |

<br>

## 3.3 SWOT Analysis

SWOT Table:

| Strengths | Weaknesses |
|-----------|------------|
| Zero cost, use of local hardware, flexibility, possibility to contribute to open-source | Dependence on quality of open-source training data, technical complexity, long training times, potentially lower accuracy than commercial solutions |
| Opportunities | Threats |
| Growth of the open-source community, increased availability of open geospatial data, possibility to create an innovative solution | Competition with commercial solutions, technology evolution, difficulty maintaining model accuracy over time |

<br>

## 3.4 Customer Value

### Unique Value Proposition (UVP)
Offer a zero-cost open-source solution for converting map images into GeoJSON, leveraging local hardware and contributing to the open-source community.

### Customer benefits
* Zero cost.
* Flexibility and customization.
* Opportunity to contribute to the project.
* Access to a user and developer community.
* Skill acquisition in deep learning and GIS.

<br>

# 4. Technical Analysis

## 4.1 Proposed Technical Solution
Use a deep learning model (e.g., U-Net, DeepLab) pre-trained on ImageNet or COCO (if applicable) and fine-tuned with an open-source dataset of map images. The application will be developed in Python with PyTorch and run locally, leveraging the GPU (RTX 3070 mobile) to accelerate training and inference.

## 4.2 Technical Requirements

### Infrastructure
* Local PC with i7 12700H, RTX 3070 mobile, 16GB RAM.
* Operating system: Linux (recommended).

### Software
* Python 3.8+
* PyTorch
* Torchvision
* OpenCV
* GeoPandas
* Rasterio

### Hardware
* NVIDIA GPU (RTX 3070 mobile)
* Multi-core CPU (i7 12700H)
* 16GB RAM
* SSD storage (recommended)

### Security
* Not applicable (if the application runs locally only).

### Scalability
* Not applicable (if the application runs locally only).

### Maintenance
* Periodic model updates with new open-source data.
* Bug fixes and issue resolution.
* Community-based user support.

<br>

## 4.3 Technical Feasibility

### Available technologies
All required technologies are currently available and open-source.

### Team skills
All developers are beginners.

### Suppliers and partners
* Open-source community.
* Open geospatial data providers.

### Technical risks
* Difficulty obtaining high-quality open-source training data.
* Complexity implementing the deep learning model with limited hardware.
* Long model training times.
* Difficulty maintaining model accuracy over time.

### Prototypes and testing
A preliminary prototype is needed to evaluate the concept feasibility and model performance on local hardware.

<br>

# 5. Financial Analysis

## 5.1 Cost Estimate
| Category        | Initial Investment     | Annual costs (€) |
|-----------------|------------------------|------------------|
| Personnel       | €0                     | €0               |
| Hardware        | €0                     | €0               |
| Software        | €0                     | €0               |
| Training        | €0                     | €0               |
| Marketing       | €0                     | €0               |
| Other           | €0                     | €0               |
| Total           | €0                     | €0               |

<br>

## 5.2 Revenue Estimate
| Revenue source  | Description            | Annual revenue (€) |
|-----------------|------------------------|---------------------|
| Sales           | €0                     | €0                  |
| Subscriptions   | €0                     | €0                  |
| Advertising     | €0                     | €0                  |
| Other           | €0                     | €0                  |
| Total           |                        | €0                  |

[Revenue projection - not applicable]

<br>

## 5.3 Profitability Indicators
Not applicable (zero cost)

<br>

## 5.4 Break-even Analysis
Not applicable (zero cost)

<br>

# 6. Organizational Analysis

## 6.1 Internal Structure

### Roles and responsibilities
* Fabio Ferro (Developer, Project Manager)
* Marrocu Mattia (UI Designer and Developer)
* Cortinovis Luca (Geospatial material researcher)

### New professional roles
* Marco Canali: Computer engineer

### Training
* Self-training through online resources and documentation.

<br>

## 6.2 Project Management Structure

### Project Manager
Fabio Ferro
### Project Team
Cortinovis Luca
Marrocu Mattia
### Management methodology

### Management tools
[Figma, GitHub]

<br>

# 7. Risk Analysis

## 7.1 Risk Identification
| Risk                       | Description                                                       | Probability (1-5) |
|----------------------------|-------------------------------------------------------------------|-------------------|
| Insufficient training data | Lack of high-quality open-source training data                    | 4                 |
| Technical complexity       | Difficulty implementing deep learning model with limited hardware | 5                 |
| Long training time         | Time required to train the model                                  | 4                 |
| Lack of motivation         | Difficulty maintaining long-term motivation                       | 3                 |
| Hardware issues            | Hardware failures that could interrupt the project                | 2                 |

<br>

# 8. Implementation Plan

## 8.1 Project Phases

1. Phase 1 - Initiation: [Define requirements, project planning, research open-source training data] - [1 month]
2. Phase 2 - Development: [Implement deep learning model, develop application, integrate with open-source GIS platforms] - [6 months]
3. Phase 3 - Testing: [Model testing, application testing, integration testing] - [1 month]
4. Phase 4 - Release (optional): [Open-source code release, documentation, community support] - [Ongoing]

<br>

## 8.2 Timeline

### Total project duration
[8 months]
### Key milestones
* Prototype completion - [2 months]
* Deep learning model completion - [6 months]
* Application completion - [7 months]
* Open-source code release (optional) - [8 months]

<br>

# 9. Conclusions and Recommendations

## 9.1 Evaluation Summary
Main advantages: Zero cost, use of local hardware, flexibility, possibility to contribute to the open-source community.
Drawbacks/Challenges: Dependence on quality of open-source training data, technical complexity, long training times, potentially lower accuracy than commercial solutions.

<br>

## 9.2 Final Recommendation
[FEASIBLE WITH CONDITIONS] - The project is feasible but requires careful planning, use of open-source software, and efficient management of local hardware resources. Focus should be on finding high-quality open-source training data, optimizing the deep learning model, and managing training time.

<br>

# X. Attachments (folder docs/fattibilita/allegati)
Some useful attachments for the feasibility study:
- List of available open-source training datasets
- Comparison of different deep learning model architectures
- Time management plan
- Gantt chart
- Risk analysis