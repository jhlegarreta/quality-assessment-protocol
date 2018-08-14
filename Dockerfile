FROM ubuntu:trusty
MAINTAINER John Pellman <john.pellman@childmind.org>

ENV AFNIPATH /opt/afni
ENV PATH /code:/opt/afni:/usr/local/bin/miniconda/bin:${PATH}

# install dependencies
RUN apt-get update && \
    apt-get install -y pkg-config graphviz gsl-bin \
                       libexpat1-dev libgiftiio-dev libglu1-mesa libglu1-mesa-dev \
                       libgsl0-dev libjpeg-progs libxml2 libxml2-dev libxext-dev \
                       libxpm-dev libxp6 libxp-dev mesa-common-dev mesa-utils \
                       netpbm libpng-dev libfreetype6-dev libxml2-dev libxslt1-dev python-dev \
                       build-essential g++ libxft2 curl

# install afni
COPY required_afni_pkgs.txt /opt/required_afni_pkgs.txt
RUN libs_path=/usr/lib/x86_64-linux-gnu && \
    if [ -f $libs_path/libgsl.so.19 ]; then \
           ln $libs_path/libgsl.so.19 $libs_path/libgsl.so.0; \
    fi && \
    mkdir -p /opt/afni && \
    curl -s https://afni.nimh.nih.gov/pub/dist/tgz/linux_openmp_64.tgz -o /tmp/linux_openmp_64.tgz  && \
    tar zxv -C /opt/afni --strip-components=1 -f /tmp/linux_openmp_64.tgz $(cat /opt/required_afni_pkgs.txt) && \
    rm /tmp/linux_openmp_64.tgz

# install miniconda
RUN curl -s https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -o /tmp/Miniconda3-latest-Linux-x86_64.sh && \
    bash /tmp/Miniconda3-latest-Linux-x86_64.sh -b -p /usr/local/bin/miniconda && \
    rm /tmp/Miniconda3-latest-Linux-x86_64.sh 
    
# install python requirements
RUN conda install -y pip scipy ipython
RUN pip install prov==1.5.0 networkx==1.11 nipype==1.1.1 python-dateutil==2.6.1 nibabel nitime pyyaml \
    pandas seaborn pyPdf2 xhtml2pdf indi-tools configparser
    
COPY . /code

RUN cd /code && \
    pip install -e .

ENTRYPOINT [ "qap_run.py" ]
