#!/bin/bash
echo "[AgriAsset] Launching iOS Version (Simulator/Device)..."
cd ..
flutter run -d ios --release
read -p "Press enter to exit..."
