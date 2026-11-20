# Reproducible build of the index benchmark (the host only has MinGW g++ 6.3, too old for ALEX/tlx).
#   docker build -t pharmatrace-bench benchmark
#   docker run --rm -v "<abs path>/benchmark/traces:/traces" -v "<abs path>/benchmark/results:/results" pharmatrace-bench
FROM gcc:14

RUN apt-get update && apt-get install -y --no-install-recommends cmake && rm -rf /var/lib/apt/lists/*

# Pinned upstream commits (recorded in results/environment.txt on every run)
ARG ALEX_COMMIT=4370da6aa8b509fdc9b0d2c49faa0624b0078589
ARG TLX_COMMIT=2dd63ab839909f0b43cd02108a1869c4670b2c8e
WORKDIR /bench
RUN git clone https://github.com/microsoft/ALEX.git third_party/alex \
 && git -C third_party/alex checkout ${ALEX_COMMIT} \
 && git clone https://github.com/tlx/tlx.git third_party/tlx \
 && git -C third_party/tlx checkout ${TLX_COMMIT}

COPY CMakeLists.txt run_all.sh ./
COPY src ./src
RUN cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j && chmod +x run_all.sh

CMD ["./run_all.sh"]
