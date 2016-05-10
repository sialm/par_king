## Synopsis

This project is designed to be used on a Raspberry Pi and a remote server. It's primary focus is to count cars entering and exiting a parking lot or garage.

## Motivation

The long term plan is to build a mobile app that can link in with this project and notify users of available parking spots.

## Installation

```bash
$ git clone git@github.com:sialm/par_king.git
```
server:
```bash
$ ./par_king/server/run <port number>
```

client:
set the values in the `client/config`
```bash
$ ./par_king/client/run <sever ip> <server port number>
```


## API Reference

For definitions of the packets see the `./par_king/constants`

## Tests

You can test software?!

## Contributors

Chen, Sherry 

Gil, Sukhdeep

Sial, Moe

Stewart, Mikio

## License

currently MIT