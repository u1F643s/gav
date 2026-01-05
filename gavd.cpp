#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <map>
#include <chrono>
#include <thread>
#include <cstdlib>   // system()
#include <algorithm> // sort
#include <csignal>
#include "nlohmann/json.hpp"

using json = nlohmann::json;

#ifdef _WIN32
#define CLEAR_CMD "cls"
#else
#define CLEAR_CMD "clear"
#endif

// ANSI colors
#define RED "\033[31m"
#define GREEN "\033[32m"
#define YELLOW "\033[33m"
#define BLUE "\033[34m"
#define RESET "\033[0m"

// Flag for graceful exit
bool stopPlayback = false;

void signalHandler(int signum) {
    stopPlayback = true;
}

void clearScreen() {
    std::system(CLEAR_CMD);
}

void printHelp() {
    std::cout << BLUE << "Usage: display.exe [options]\n" << RESET;
    std::cout << "Options:\n";
    std::cout << "  -h                Show this help message\n";
    std::cout << "  -json <file>      JSON file with frames (default: output.json)\n";
    std::cout << "  -path <dir>       Directory containing the JSON file (default: current directory)\n";
    std::cout << "  -fps <number>     Frames per second (default: 20)\n";
    std::cout << "  -startframe <n>   Start playback from frame n (default: 1)\n";
    std::cout << "  -endframe <n>     Stop playback at frame n (default: last frame)\n";
}

std::map<std::string, std::string> loadFrames(const std::string& jsonPath) {
    std::ifstream file(jsonPath);
    if (!file.is_open()) {
        std::cerr << RED << "Error: File '" << jsonPath << "' not found!" << RESET << std::endl;
        exit(1);
    }

    json j;
    try {
        file >> j;
    }
    catch (json::parse_error& e) {
        std::cerr << RED << "Error: Invalid JSON file - " << e.what() << RESET << std::endl;
        exit(1);
    }

    if (!j.contains("frames")) {
        std::cerr << RED << "Error: JSON does not contain 'frames' key" << RESET << std::endl;
        exit(1);
    }

    std::map<std::string, std::string> frames;
    for (auto& [key, value] : j["frames"].items()) {
        frames[key] = value;
    }

    return frames;
}

void playFrames(const std::map<std::string, std::string>& frames, int fps, int startFrame, int endFrame) {
    std::vector<std::string> keys;
    for (auto& [k, _] : frames) keys.push_back(k);
    std::sort(keys.begin(), keys.end());

    int totalFrames = keys.size();
    if (startFrame < 1) startFrame = 1;
    if (endFrame > totalFrames || endFrame < 1) endFrame = totalFrames;

    double frameDelay = 1.0 / fps;

    std::cout << BLUE << "Press Enter to start playback..." << RESET << std::endl;
    std::cin.get();

    for (int i = startFrame - 1; i < endFrame && !stopPlayback; ++i) {
        clearScreen();
        std::cout << frames.at(keys[i]) << std::endl;
        std::cout << BLUE << "[Frame " << i + 1 << "/" << totalFrames << "]" << RESET << std::flush;
        std::this_thread::sleep_for(std::chrono::duration<double>(frameDelay));
    }

    if (stopPlayback)
        std::cout << "\n" << YELLOW << "Playback stopped." << RESET << std::endl;
    else
        std::cout << "\n\n" << GREEN << "Playback complete!" << RESET << std::endl;
}

int main(int argc, char* argv[]) {
    signal(SIGINT, signalHandler); // Ctrl+C handling

    std::string jsonPath = "output.json";
    std::string dirPath = "";
    int fps = 20;
    int startFrame = 1;
    int endFrame = -1; // -1 means last frame

    // Parse arguments
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "-h") {
            printHelp();
            return 0;
        }
        else if (arg == "-json" && i + 1 < argc) jsonPath = argv[++i];
        else if (arg == "-path" && i + 1 < argc) dirPath = argv[++i];
        else if (arg == "-fps" && i + 1 < argc) fps = std::stoi(argv[++i]);
        else if (arg == "-startframe" && i + 1 < argc) startFrame = std::stoi(argv[++i]);
        else if (arg == "-endframe" && i + 1 < argc) endFrame = std::stoi(argv[++i]);
        else {
            std::cerr << RED << "Unknown argument: " << arg << RESET << std::endl;
            return 1;
        }
    }

    // If dirPath is set, prepend it to jsonPath
    if (!dirPath.empty()) {
#ifdef _WIN32
        if (dirPath.back() != '\\' && dirPath.back() != '/') dirPath += '\\';
#else
        if (dirPath.back() != '/') dirPath += '/';
#endif
        jsonPath = dirPath + jsonPath;
    }

    std::cout << BLUE << "Loading JSON file: " << jsonPath << RESET << std::endl;
    auto frames = loadFrames(jsonPath);
    std::cout << GREEN << "Loaded " << frames.size() << " frames" << RESET << std::endl;
    std::cout << YELLOW << "FPS: " << fps << RESET << std::endl;

    if (endFrame == -1) endFrame = frames.size(); // default to last frame

    playFrames(frames, fps, startFrame, endFrame);

    return 0;
}
