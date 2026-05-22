FROM node:20-alpine
WORKDIR /app
COPY package.json /app/package.json
RUN npm install
COPY . /app
RUN chmod +x /app/scripts/entrypoint.sh
EXPOSE 3000
CMD ["/app/scripts/entrypoint.sh"]
