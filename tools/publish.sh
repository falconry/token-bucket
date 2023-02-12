DIST_DIR=./dist

read -p "Sign and upload $DIST_DIR/* to PyPI? [y/N]: " CONTINUE

if [[ $CONTINUE =~ ^[Yy]$ ]]; then
    hatch publish $DIST_DIR/*
fi
