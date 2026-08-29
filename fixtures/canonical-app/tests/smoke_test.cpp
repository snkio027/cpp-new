#include <string_view>

int main() {
    constexpr std::string_view project_name{"robot-runtime"};
    return project_name.empty() ? 1 : 0;
}
