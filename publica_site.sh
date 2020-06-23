mkdocs build -f docs/site/mkdocs.yml
rm -rf /var/www/html/ficha_site/*
cp -R docs/site/site/* /var/www/html/ficha_site/
