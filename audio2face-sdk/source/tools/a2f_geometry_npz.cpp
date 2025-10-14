// CLI: read WAV, run A2F geometry (regression/diffusion), dump geometry to NPZ
#include "audio2face/audio2face.h"
#include "audio2face/parse_helper.h"
#include "audio2x/cuda_utils.h"
#include "audio2x/audio_accumulator.h"
#include "AudioFile.h"
#include <cxxopts.hpp>
#include <iostream>
#include <vector>
#include <string>
#include <stdexcept>
#include "cnpy.h"

template <typename T> struct Destroyer { void operator()(T* p) const { if (p) p->Destroy(); } };
template <typename T> using UniquePtr = std::unique_ptr<T, Destroyer<T>>;
template <typename T> UniquePtr<T> ToUniquePtr(T* p) { return UniquePtr<T>(p); }

static std::vector<float> readAudioMono16k(const std::string& path) {
    AudioFile<float> audio;
    if (!audio.load(path)) throw std::runtime_error("Failed to load audio: " + path);
    if (audio.getSampleRate() != 16000) throw std::runtime_error("Expected 16kHz WAV input");
    if (audio.getNumChannels() < 1) throw std::runtime_error("No audio channels");
    return audio.samples[0];
}

int main(int argc, char** argv) {
    try {
        cxxopts::Options options("a2f_geometry_npz", "Audio2Face geometry -> NPZ");
        options.add_options()
            ("i,input", "Input WAV (16kHz)", cxxopts::value<std::string>())
            ("type", "Model type: regression|diffusion", cxxopts::value<std::string>()->default_value("regression"))
            ("model", "Model JSON (geometry model.json)", cxxopts::value<std::string>())
            ("identity", "Diffusion identity index", cxxopts::value<int>()->default_value("0"))
            ("fps", "Target FPS for geometry", cxxopts::value<int>()->default_value("60"))
            ("o,output", "Output NPZ path", cxxopts::value<std::string>())
            ("h,help", "Help");
        auto result = options.parse(argc, argv);
        if (result.count("help") || !result.count("input") || !result.count("model") || !result.count("output")) {
            std::cout << options.help() << std::endl;
            return 2;
        }
        const std::string inputWav = result["input"].as<std::string>();
        const std::string modelJson = result["model"].as<std::string>();
        const std::string type = result["type"].as<std::string>();
        const int fps = result["fps"].as<int>();
        const int identity = result["identity"].as<int>();
        const std::string outPath = result["output"].as<std::string>();

        auto audioBuf = readAudioMono16k(inputWav);
        auto cudaStream = ToUniquePtr(nva2x::CreateCudaStream());
        if (!cudaStream) throw std::runtime_error("CUDA stream failed");

        // Geometry executors (not blendshape solver): we want raw geometry
        nva2f::IGeometryExecutorBundle* rawBundle = nullptr;
        if (type == "regression") {
            nva2f::IRegressionModel::IGeometryModelInfo* tmp = nullptr;
            rawBundle = nva2f::ReadRegressionGeometryExecutorBundle(1, modelJson.c_str(), nva2f::IGeometryExecutor::ExecutionOption::All, static_cast<std::size_t>(fps), 1, &tmp);
            if (!rawBundle || !tmp) throw std::runtime_error("Regression geometry bundle failed");
            tmp->Destroy();
        } else if (type == "diffusion") {
            nva2f::IDiffusionModel::IGeometryModelInfo* tmp = nullptr;
            rawBundle = nva2f::ReadDiffusionGeometryExecutorBundle(1, modelJson.c_str(), nva2f::IGeometryExecutor::ExecutionOption::All, static_cast<std::size_t>(identity), true, &tmp);
            if (!rawBundle || !tmp) throw std::runtime_error("Diffusion geometry bundle failed");
            tmp->Destroy();
        } else {
            throw std::runtime_error("Unknown type: " + type);
        }
        UniquePtr<nva2f::IGeometryExecutorBundle> bundle(rawBundle);

        // Minimal neutral emotion to unblock geometry
        {
            auto& emoAcc = bundle->GetEmotionAccumulator(0);
            std::vector<float> neutral(10, 0.0f);
            emoAcc.Accumulate(0, nva2x::HostTensorFloatConstView{neutral.data(), neutral.size()}, bundle->GetCudaStream().Data());
            emoAcc.Close();
        }

        // Accumulate audio
        bundle->GetAudioAccumulator(0).Accumulate(nva2x::HostTensorFloatConstView{audioBuf.data(), audioBuf.size()}, bundle->GetCudaStream().Data());
        bundle->GetAudioAccumulator(0).Close();

        auto& exec = bundle->GetExecutor();

        const std::size_t skinSize = exec.GetSkinGeometrySize();
        const std::size_t tongueSize = exec.GetTongueGeometrySize();
        const std::size_t jawSize = exec.GetJawTransformSize();
        const std::size_t eyesSize = exec.GetEyesRotationSize();

        std::vector<float> skinAll;  // concatenated frames
        std::vector<float> tongueAll;
        std::vector<float> jawAll;
        std::vector<float> eyesAll;
        std::vector<long long> tsAll;

        auto cb = [&](void* /*ud*/, const nva2f::IGeometryExecutor::Results& r) {
            tsAll.push_back(static_cast<long long>(r.timeStampCurrentFrame));
            if (skinSize && r.skinGeometry.Size()) {
                std::vector<float> host(r.skinGeometry.Size());
                nva2x::CopyDeviceToHost({host.data(), host.size()}, r.skinGeometry, r.skinCudaStream);
                skinAll.insert(skinAll.end(), host.begin(), host.end());
            }
            if (tongueSize && r.tongueGeometry.Size()) {
                std::vector<float> host(r.tongueGeometry.Size());
                nva2x::CopyDeviceToHost({host.data(), host.size()}, r.tongueGeometry, r.tongueCudaStream);
                tongueAll.insert(tongueAll.end(), host.begin(), host.end());
            }
            if (jawSize && r.jawTransform.Size()) {
                std::vector<float> host(r.jawTransform.Size());
                nva2x::CopyDeviceToHost({host.data(), host.size()}, r.jawTransform, r.jawCudaStream);
                jawAll.insert(jawAll.end(), host.begin(), host.end());
            }
            if (eyesSize && r.eyesRotation.Size()) {
                std::vector<float> host(r.eyesRotation.Size());
                nva2x::CopyDeviceToHost({host.data(), host.size()}, r.eyesRotation, r.eyesCudaStream);
                eyesAll.insert(eyesAll.end(), host.begin(), host.end());
            }
        };
        exec.SetResultsCallback(cb, nullptr);
        while (nva2x::GetNbReadyTracks(exec) > 0) exec.Execute(nullptr);

        // Save NPZ: 1D flat arrays + shapes metadata are implicit; consumers must reshape accordingly
        // keys: timestamps_ms, skin, tongue, jaw, eyes; also sizes: skin_size, tongue_size, jaw_size, eyes_size
        cnpy::npz_save(outPath.c_str(), "timestamps_ms", tsAll.data(), {tsAll.size()}, "w");
        if (!skinAll.empty()) cnpy::npz_save(outPath.c_str(), "skin", skinAll.data(), {skinAll.size()}, "a");
        if (!tongueAll.empty()) cnpy::npz_save(outPath.c_str(), "tongue", tongueAll.data(), {tongueAll.size()}, "a");
        if (!jawAll.empty()) cnpy::npz_save(outPath.c_str(), "jaw", jawAll.data(), {jawAll.size()}, "a");
        if (!eyesAll.empty()) cnpy::npz_save(outPath.c_str(), "eyes", eyesAll.data(), {eyesAll.size()}, "a");
        // sizes
        long long skinSz = static_cast<long long>(skinSize);
        long long tongueSz = static_cast<long long>(tongueSize);
        long long jawSz = static_cast<long long>(jawSize);
        long long eyesSz = static_cast<long long>(eyesSize);
        cnpy::npz_save(outPath.c_str(), "skin_size", &skinSz, {1}, "a");
        cnpy::npz_save(outPath.c_str(), "tongue_size", &tongueSz, {1}, "a");
        cnpy::npz_save(outPath.c_str(), "jaw_size", &jawSz, {1}, "a");
        cnpy::npz_save(outPath.c_str(), "eyes_size", &eyesSz, {1}, "a");

        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
}


