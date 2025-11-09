FROM haditsn/odoo18:base

#COPY custom_addons /usr/lib/python3/dist-packages/odoo/custom_addons
USER root
#RUN apt-get update && apt-get install -y fonts-dejavu-core fonts-dejavu-extra fonts-freefont-ttf \ 
#     fonts-noto fonts-noto-cjk fonts-noto-color-emoji \
#     fonts-noto-extra fonts-noto-ui-core \ 
#     fonts-noto-unhinted fonts-noto-core fonts-vazirmatni  && fc-cache -f -v


RUN apt-get update && \
    apt-get install -y wget unzip \
    fonts-dejavu-core fonts-dejavu-extra fonts-freefont-ttf \
    fonts-noto fonts-noto-cjk fonts-noto-color-emoji \
    fonts-noto-extra fonts-noto-ui-core \
    fonts-noto-unhinted fonts-noto-core && \
    wget -q https://github.com/rastikerdar/vazirmatn/releases/download/v33.003/vazirmatn-v33.003.zip  -O /tmp/vazirmatn.zip && \
    unzip /tmp/vazirmatn.zip -d /usr/share/fonts/truetype/vazirmatn && \
    fc-cache -f -v && \
    rm -rf /tmp/vazirmatn.zip /var/lib/apt/lists/*


#RUN apt-get install -y --only-upgrade libtiff6 && apt-get clean
RUN apt-get update && \
    apt-get install -y --only-upgrade libtiff6 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade s3fs --break-system-packages

COPY GeoLite2-City.mmdb /usr/share/GeoIP/GeoLite2-City.mmdb
COPY custom_addons /usr/lib/python3/dist-packages/odoo/custom_addons
#RUN pip3 install   tqdm  --break-system-packages
#RUN   pip install -U "s3fs>=2024.3.0" "fsspec>=2024.3.0" "aiobotocore>=2.13.0"  --break-system-packages
#RUN odoo -u all -d template_db --stop-after-init


#RUN python3 -m venv /opt/venv \
#    && /opt/venv/bin/pip install --upgrade pip \
#    && /opt/venv/bin/pip install num2fawords

#ENV PATH="/opt/venv/bin:$PATH"
#RUN pip install --upgrade pip && pip install num2fawords
#RUN apt-get update && apt-get install -y python3-num2fawords

#USER root
#RUN  chown -R odoo:odoo /usr/lib/python3/dist-packages/odoo/custom_addons 
#USER odoo

