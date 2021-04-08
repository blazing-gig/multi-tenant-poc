FROM node:14-buster-slim As builder

WORKDIR /code

ENV PATH /code/node_modules/.bin:$PATH

COPY package.json package-lock.json ./

RUN npm install

COPY . .

RUN ng build --prod --aot

FROM nginx:stable

COPY --from=builder /code/dist/demo-app/ /usr/share/nginx/html

COPY ./nginx.default.conf /etc/nginx/conf.d/default.conf

