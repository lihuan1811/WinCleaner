cmake_minimum_required(VERSION 3.21)

project(ClearC VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTORCC ON)

find_package(Qt6 6.5 REQUIRED COMPONENTS Core Gui Widgets Concurrent)

qt_add_executable(ClearC
    WIN32
    src/main.cpp
    src/MainWindow.h
    src/MainWindow.cpp
    src/CleanupEngine.h
    src/CleanupEngine.cpp
    src/SystemCatalog.h
    src/SystemCatalog.cpp
    src/AccountStore.h
    src/AccountStore.cpp
)

target_link_libraries(ClearC
    PRIVATE
        Qt6::Core
        Qt6::Gui
        Qt6::Widgets
        Qt6::Concurrent
)

target_compile_options(ClearC PRIVATE
    $<$<CXX_COMPILER_ID:MSVC>:/utf-8>
)

set_target_properties(ClearC PROPERTIES
    OUTPUT_NAME "ClearC"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)

install(TARGETS ClearC RUNTIME DESTINATION .)
