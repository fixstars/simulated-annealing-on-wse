use clap::Parser;
use rand::SeedableRng as _;
use rayon::prelude::*;
use std::path::{Path, PathBuf};

fn inner_product<I1: Iterator, I2: Iterator, T>(x: I1, y: I2) -> T
where
    <I1 as Iterator>::Item: std::ops::Mul<<I2 as Iterator>::Item>,
    T: std::iter::Sum<<<I1 as Iterator>::Item as std::ops::Mul<<I2 as Iterator>::Item>>::Output>,
{
    x.zip(y).map(|(x, y)| x * y).sum()
}

#[derive(Debug, Clone)]
struct Qubo {
    n: usize,
    q: Box<[f32]>,
    s: Box<[u8]>,
}

impl Qubo {
    fn from_ndarray(q: ndarray::Array2<f32>) -> Self {
        let [n, m] = q.shape() else { unreachable!() };
        let [s1, s2] = q.strides() else {
            unreachable!()
        };
        assert_eq!(n, m);
        let n = *n;
        assert_eq!(*s1 as usize, n);
        assert_eq!(*s2, 1);
        let (q, _) = q.into_raw_vec_and_offset();
        Self {
            n,
            q: q.into_boxed_slice(),
            s: vec![0; n].into_boxed_slice(),
        }
    }
    fn flip_energy(&self, i: usize) -> f32 {
        let t = self.q.split_at(i * self.n).1;
        let qi = t.split_at(self.n).0;
        let fs = self.s.iter().map(|s_j| *s_j as f32);
        let e = inner_product::<_, _, f32>(fs, qi.iter());
        if self.s[i] == 1 {
            // s_i : 1 -> 0
            // \delta E = -(\sum_{j \neq i} Q_{ij} s_j + Q_{ii})
            -e
        } else {
            // s_i : 0 -> 1
            // \delta E = \sum_{j \neq i} Q_{ij} s_j + Q_{ii}
            qi[i] + e
        }
    }
    fn search_temperature(&mut self, rng: &mut impl rand::Rng, iters: u64) {
        let mut v = Vec::<ordered_float::OrderedFloat<f32>>::with_capacity(self.n);
        for _ in 0..iters {
            for si in self.s.iter_mut() {
                *si = rng.gen_range(0..2);
            }
            let mut w = (0..self.n)
                .into_par_iter()
                .map(|i| self.flip_energy(i))
                .filter(|d| *d > 0.0)
                .map(ordered_float::OrderedFloat)
                .collect::<Vec<_>>();
            v.append(&mut w);
        }
        let n = v.len();
        v.sort_unstable();
        println!("Percentile, Temperature, log_init_temperature");
        for i in [1, 5, 10, 25, 50, 75, 90, 95, 99] {
            let t = v[n * i / 100].0;
            println!(
                "{i:2}%, {t:8.3}, {:8.0}",
                ((2.0 * t).ln() * 256.0).floor() + 32768.0
            );
        }
    }
}

fn read_npy(p: &Path) -> ndarray::Array2<f32> {
    use ndarray::ShapeBuilder;
    let bytes = std::fs::read(p).unwrap();
    let reader = npyz::NpyFile::new(&bytes[..]).unwrap();
    let shape = Box::<[_]>::from(reader.shape());
    let order = reader.order();

    let npyz::DType::Plain(s) = reader.dtype() else {
        panic!("plain type expected")
    };
    assert_eq!(s.type_char(), npyz::TypeChar::Float);
    let typename;
    let data = if s.size_field() == 4 {
        typename = "f32";
        reader.into_vec::<f32>().unwrap()
    } else {
        typename = "f64";
        let data = reader.into_vec::<f64>().unwrap();
        data.into_iter().map(|x| x as f32).collect()
    };
    match shape[..] {
        [l] => {
            println!("input is [{typename}; {l}]");
            // solve x * (x + 1) / 2 = l
            let x = ((8.0 * (l as f64) + 1.0).sqrt() - 1.0) / 2.0;
            let n = x.round() as usize;
            println!("n = {n}");
            let mut r = ndarray::Array2::zeros([n, n]);
            let mut i = 0;
            let mut j = 0;
            for v in data.into_iter() {
                r[[i, j]] = v;
                r[[j, i]] = v;
                i += 1;
                if i >= n {
                    j += 1;
                    i = j; // upper triangle
                }
            }
            r
        }
        [i1, i2] => {
            println!("input is [[{typename}; {i1}]; {i2}]");
            println!("n = {i1}");
            let shape = [i1 as usize, i2 as usize];
            let true_shape = shape.set_f(order == npyz::Order::Fortran);
            ndarray::Array2::from_shape_vec(true_shape, data)
                .unwrap_or_else(|e| panic!("shape error: {}", e))
        }
        _ => panic!("expected 1D or 2D array"),
    }
}

#[derive(Parser, Debug)]
struct Args {
    /// npy file of Q
    #[arg(short, long)]
    file: PathBuf,
    /// number of iteration
    #[arg(short, long, default_value_t = 100)]
    iters: u64,
}

fn main() {
    let args = Args::parse();
    let q = read_npy(&args.file);
    println!("{:?}", q);
    let mut qubo = Qubo::from_ndarray(q);
    let mut rng = rand_pcg::Pcg64::seed_from_u64(rand::random());
    qubo.search_temperature(&mut rng, args.iters);
}
