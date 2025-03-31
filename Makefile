INSTALL.html: INSTALL.md Makefile
	pandoc --filter pandoc-sidenote --template=.pandoc/templates/template.html5 \
		--css=.pandoc/css/theme.css  \
		--css=.pandoc/css/skylighting-solarized-theme.css \
		--embed-resources --standalone\
		-o INSTALL.html  INSTALL.md 
