# Build up on local docker image placed in ..
FROM evic
#
# It is needed to once run before building this Dockerfile:
# cd .. && docker build . -t evic

ENV DEBIAN_FRONTEND=noninteractive
RUN echo 'APT::Get::Assume-Yes "true";' >> /etc/apt/apt.conf

RUN apt install emacs-nox \
                git
RUN mkdir ~/.emacs.d

COPY init.el /root/.emacs.d/init.el

WORKDIR /usr/local/src/evidential-calculator

# Install needed packages
RUN emacs --batch --load /root/.emacs.d/init.el

# Start up emacs on launch, drop into bash after C-x C-c
CMD ["bash", "-c", "emacs --load /root/.emacs.d/init.el; /bin/bash"]
