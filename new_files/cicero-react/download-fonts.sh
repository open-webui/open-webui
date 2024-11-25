#!/bin/bash

# Create fonts directory if it doesn't exist
mkdir -p src/fonts

# Download Inter fonts
curl -L -o src/fonts/Inter-Regular.woff2 "https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZ9hiA.woff2"
curl -L -o src/fonts/Inter-Italic.woff2 "https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZFhiA.woff2"
curl -L -o src/fonts/Inter-SemiBold.woff2 "https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuI6fAZ9hiA.woff2"
curl -L -o src/fonts/Inter-SemiBoldItalic.woff2 "https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuI6fAZFhiA.woff2"
curl -L -o src/fonts/Inter-Bold.woff2 "https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuGKYAZ9hiA.woff2"
curl -L -o src/fonts/Inter-BoldItalic.woff2 "https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuGKYAZFhiA.woff2"

# Download Roboto Mono fonts
curl -L -o src/fonts/RobotoMono-Regular.woff2 "https://fonts.gstatic.com/s/robotomono/v23/L0xuDF4xlVMF-BfR8bXMIhJHg45mwgGEFl0_3vq_ROW4.woff2"
curl -L -o src/fonts/RobotoMono-Italic.woff2 "https://fonts.gstatic.com/s/robotomono/v23/L0xoDF4xlVMF-BfR8bXMIjhOsXG-q2oeuFoqFrlnANW3CpmMSQ.woff2"
curl -L -o src/fonts/RobotoMono-Bold.woff2 "https://fonts.gstatic.com/s/robotomono/v23/L0xuDF4xlVMF-BfR8bXMIhJHg45mwgGEFl0_7Pq_ROW4.woff2"
