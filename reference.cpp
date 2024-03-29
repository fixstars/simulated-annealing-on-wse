#include <iostream> // ng
#include <vector> // ng, 2d array -> ok
#include <ranges>// ok
#include <cmath> // exp -> ok

uint32_t state = 0x103; // random

namespace global {
    float T = 1000;
    int N = 5;
    float inputs[] = {
        0.2, 0.5, -1.0, 0.5, 2.3,
        1.2, 5.2, 2.4, 6.0,
        0.1, 0.2, 0.5,
        -0.8, -2.8,
        1.2
    };
}

// https://ja.wikipedia.org/wiki/Xorshift
uint32_t xorshift32()
{
	/* Algorithm "xor" from p. 4 of Marsaglia, "Xorshift RNGs" */
	uint32_t x = state;
	x ^= x << 13;
	x ^= x >> 17;
	x ^= x << 5;
	return state = x;
}

// assuming this is a fixed-point number and converting it
float rand_float_zero2one()
{
    const uint32_t rand = xorshift32();
    float ret = 0;
    float tmp = 1;
    for (int i : std::views::iota(0, 32) )
    {
        tmp /= 2;
        const bool bit = rand & (1 << i);
        ret += tmp * bit;
    }
    return ret;
}

// a < b
float rand_dist(float a, float b)
{
    const auto range = (b - a);
    const auto raw = rand_float_zero2one();
    auto ret = range * raw;
    ret += a;
    return ret;
}

// Biased but minor and ignored.
// a < b
int rand_int(int a, int b)
{
    const auto range = b - a;
    const auto rand = xorshift32();
    int ret = rand % range;
    return ret + a;
}

void test_rand_dist()
{
    for (int i : std::views::iota(0, 32) )
    {
        std::cout << rand_float_zero2one() << std::endl;
        std::cout << rand_dist(-2, 2) << std::endl;
    }
}

class Model {
protected:
    int N;
    std::vector<int> s;
    std::vector<std::vector<float>> Q;

public:
    Model(int N) :
        N(N),
        s(std::vector<int>(N)),
        Q(std::vector<std::vector<float>>(N, std::vector<float>(N))) {}
    virtual ~Model() = default;

    int size() const { return N; }

    void read_Q(float * inputs) {
        float v;
        int counter = 0;
        for (int i : std::views::iota(0, N)) {
            for (int j : std::views::iota(i, N)) {
                v = inputs[counter++];
                Q[i][j] = Q[j][i] = v;
            }
        }
    }

    const std::vector<int>& get_s() const {
        return s;
    }

    float energy() const {
        float ene = 0.0;
        for (int i : std::views::iota(0, N)) {
            for (int j : std::views::iota(0, N) | std::views::filter([i](int n) { return i < n; }))
                ene += Q[i][j] * s[i] * s[j];
            ene += Q[i][i] * s[i];
        }
        return ene;
    }

    void print() {
        std::cerr << energy() << " : ";
        for (int i : std::views::iota(0, N))
            std::cerr << s[i] << " ";
        std::cerr << std::endl;
    }

    virtual void setup() = 0;
    virtual void flip(int i) = 0;
    virtual float flip_energy(int i) const = 0;
};

class Ising : public Model {
public:
    Ising(int N) : Model(N) {}
    virtual ~Ising() = default;

    void setup() override {
        for (int i : std::views::iota(0, N)) s[i] = 1;
        for (int i : std::views::iota(0, N))
        {
            for (int j : std::views::iota(0, N))
            {
                Q[i][j] = rand_dist(-1.0, 1.0);
            }
        }
    }

    void flip(int i) override { s[i] *= -1; }

    float flip_energy(int i) const override {
        float ene = 0.0;
        for (int j : std::views::iota(0, N) | std::views::filter([i](int n) { return i != n; }))
            ene += Q[i][j] * s[i] * s[j];
        ene += Q[i][i] * s[i];
        return -2.0 * ene;
    }
};

class QUBO : public Model {
public:
    QUBO(int N) : Model(N) {}
    virtual ~QUBO() = default;
    
    void setup() override {
        for (int i : std::views::iota(0, N)) s[i] = 1;
        for (int i : std::views::iota(0, N))
            for (int j : std::views::iota(0, N))
                Q[i][j] = i != j ? rand_dist(-1.0, 1.0) : 0.0;
    }

    void flip(int i) override { s[i] ^= 1; }

    float flip_energy(int i) const override {
        float ene = 0.0;
        for (int j : std::views::iota(0, N) | std::views::filter([i](int n) { return i != n; }))
            ene += Q[i][j] /* *1 */ * s[j];
        ene += Q[i][i] /* *1 */;
        return ene * (s[i] == 0 ? 1.0 : -1.0);
    }
};

void anneal(Model* model, int max_iters, float t, float alpha, float tm, std::vector<int>& best_s) {
    float current_energy = model->energy();
    float min_energy = current_energy;
    best_s = model->get_s();
    for ([[maybe_unused]] int i : std::views::iota(0) | std::views::take_while([tm, max_iters](int i) {
            return (max_iters < 0 || i < max_iters);
        } ))
    {
        t *= alpha;
        int idx = rand_int(0, model->size() - 1);
        float d = model->flip_energy(idx);
        if (d < 0.0 || std::exp(-d / t) > rand_dist(0.0, 1.0)) {
            current_energy += d;
            model->flip(idx);
            if (current_energy < min_energy) {
                min_energy = current_energy;
                best_s = model->get_s();
            }
        }
    }
}

int main(int argc, char* argv[]) {
    std::string target_model = argc > 1 ? argv[1] : "qubo";

    Model* model = target_model.compare("qubo") == 0 ? static_cast<Model*>(new QUBO(global::N)) : new Ising(global::N);

    model->setup();
    model->read_Q(global::inputs);

    int max_iters = 4096;  // max_iterations; -1:unlimited; something big number
    float alpha = 1.0 - 0.04 / global::T;  // damping_factor
    float temp = std::fabs(model->energy());  // init_temperature

    float C = 32.4;

    std::vector<int> best_s;
    anneal(model, max_iters, temp, alpha, global::T, best_s);

    for (int x : best_s) std::cout << x << " ";
    std::cout << std::endl;

    delete model;

    // test_rand_dist();

    return 0;
}
