FROM mcr.microsoft.com/playwright:v1.44.0-jammy

WORKDIR /app

COPY package.json ./
RUN npm install --omit=dev

COPY run.js ./

# Output directory — mount a host volume here at runtime
RUN mkdir -p /output

ENV ASSAY_TARGET_URL=""
ENV ASSAY_SUITE="default"
ENV ASSAY_OUTPUT_DIR="/output"

CMD ["node", "run.js"]
