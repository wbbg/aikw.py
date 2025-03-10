INSTALL.html: INSTALL.md
	pandoc --filter pandoc-sidenote --template=.pandoc/templates/template.html5 \
		--css=.pandoc/css/theme.css  \
		--css=.pandoc/css/skylighting-solarized-theme.css \
		-o INSTALL.html  INSTALL.md 
