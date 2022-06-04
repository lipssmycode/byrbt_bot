FROM ubuntu:18.04
LABEL maintainer="Base BYRBT-BOT Image By SMYYAN"
ENV PYTHONUNBUFFERED TRUE

USER root
WORKDIR /root

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
    ca-certificates \
    g++ \
    curl \
    build-essential \
    zlib1g-dev \
    libncurses5-dev \
    libgdbm-dev \
    libnss3-dev \
    libssl-dev \
    libreadline-dev \
    libffi-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*
RUN wget https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/Miniconda3-py37_4.9.2-Linux-x86_64.sh -O ~/conda.sh
RUN /bin/bash ~/conda.sh -b -p /conda && rm -rf ~/conda.sh

RUN echo '\n\
__conda_setup="$('/conda/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"\n\
if [ $? -eq 0 ]; then\n\
    eval "$__conda_setup"\n\
else\n\
    if [ -f "conda/etc/profile.d/conda.sh" ]; then\n\
        . "conda/etc/profile.d/conda.sh"\n\
    else\n\
        export PATH="conda/bin:$PATH"\n\
    fi\n\
fi\n\
unset __conda_setup\n'\
>> ~/.bashrc && /bin/bash -c 'source ~/.bashrc'

RUN mkdir ~/.pip && \
    cd ~/.pip && \
echo "\
[global]\n\
index-url = https://mirrors.aliyun.com/pypi/simple/\n\
\n\
[install]\n\
trusted-host=mirrors.aliyun.com\n"\
> ~/.pip/pip.conf

RUN echo "\
channels:\n\
   - defaults\n\
show_channel_urls: true\n\
channel_alias: https://mirrors.tuna.tsinghua.edu.cn/anaconda\n\
default_channels:\n\
   - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main\n\
   - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free\n\
   - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r\n\
   - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/pro\n\
   - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/msys2\n\
custom_channels:\n\
   conda-forge: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud\n\
   msys2: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud\n\
   bioconda: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud\n\
   menpo: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud\n\
   pytorch: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud\n\
   simpleitk: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud\n"\
 > ~/.condarc

RUN ls -l /conda/bin |grep ^-| awk '{cmd1="mv /usr/bin/"$9" /usr/bin/"$9".bak 2>/dev/null";system(cmd1);cmd="ln -s /conda/bin/"$9" /usr/bin/"$9;system(cmd)}'
RUN ln -s /conda/bin/python3.7 /usr/bin/python3
RUN ln -s /conda/bin/python3.7 /usr/bin/python

WORKDIR /

COPY . ./

RUN chmod 777 ./config/config.ini
RUN pip install -i https://mirrors.aliyun.com/pypi/simple -r requirements.txt

CMD ["python3","bot.py"]
