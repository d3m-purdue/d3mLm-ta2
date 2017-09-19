install.packages('curl', lib='./rlib', repos='http://cran.rstudio.com')
install.packages('devtools', lib='./rlib', repos='http://cran.rstudio.com')
install.packages('httr', lib='./rlib', repos='http://cran.rstudio.com')
install.packages('withr', lib='./rlib', repos='http://cran.rstudio.com')

library(curl, lib.loc='./rlib')
library(withr, lib.loc='./rlib')
library(devtools, lib.loc='./rlib')
library(httr, lib.loc='./rlib')

options(unzip="internal")
withr::with_libpaths(new="./rlib", code=devtools::install_github('d3m-purdue/d3mLm'))
