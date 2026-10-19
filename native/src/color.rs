use serde::{Deserialize, Serialize};
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Light {
    pub on: bool,
    pub mode: String,
    pub white: u16,
    pub temperature: u16,
    pub h: u16,
    pub s: u16,
    pub v: u16,
}
impl Default for Light {
    fn default() -> Self {
        Self {
            on: false,
            mode: "white".into(),
            white: 10,
            temperature: 0,
            h: 0,
            s: 1000,
            v: 10,
        }
    }
}
pub fn hsv_rgb(h: u16, s: u16, v: u16) -> [u8; 3] {
    let h = (h as f64 % 360.) / 60.;
    let s = s as f64 / 1000.;
    let v = v as f64 / 1000.;
    let c = v * s;
    let x = c * (1. - (h % 2. - 1.).abs());
    let m = v - c;
    let a = match h as u8 {
        0 => [c, x, 0.],
        1 => [x, c, 0.],
        2 => [0., c, x],
        3 => [0., x, c],
        4 => [x, 0., c],
        _ => [c, 0., x],
    };
    a.map(|n| ((n + m) * 255.).round().clamp(0., 255.) as u8)
}
pub fn rgb_hsv(rgb: [u8; 3], previous_h: u16) -> (u16, u16, u16) {
    let [r, g, b] = rgb.map(|n| n as f64 / 255.);
    let max = r.max(g).max(b);
    let min = r.min(g).min(b);
    let d = max - min;
    let h = if d == 0. {
        previous_h as f64
    } else if max == r {
        60. * ((g - b) / d).rem_euclid(6.)
    } else if max == g {
        60. * ((b - r) / d + 2.)
    } else {
        60. * ((r - g) / d + 4.)
    };
    (
        h.round() as u16,
        if max == 0. {
            0
        } else {
            (d / max * 1000.).round() as u16
        },
        (max * 1000.).round() as u16,
    )
}
pub fn parse_hex(s: &str) -> Option<[u8; 3]> {
    let s = s.trim().strip_prefix('#').unwrap_or(s.trim());
    if s.len() != 6 || !s.is_ascii() {
        return None;
    }
    Some([
        u8::from_str_radix(&s[0..2], 16).ok()?,
        u8::from_str_radix(&s[2..4], 16).ok()?,
        u8::from_str_radix(&s[4..6], 16).ok()?,
    ])
}
pub fn hex(rgb: [u8; 3]) -> String {
    format!("#{:02X}{:02X}{:02X}", rgb[0], rgb[1], rgb[2])
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn primaries() {
        assert_eq!(hsv_rgb(0, 1000, 1000), [255, 0, 0]);
        assert_eq!(hsv_rgb(120, 1000, 1000), [0, 255, 0]);
        assert_eq!(hsv_rgb(360, 1000, 1000), [255, 0, 0]);
    }
    #[test]
    fn gray_keeps_hue() {
        assert_eq!(rgb_hsv([128, 128, 128], 233), (233, 0, 502));
        assert_eq!(hsv_rgb(233, 0, 0), [0, 0, 0]);
    }
    #[test]
    fn rgb_roundtrips() {
        for r in (0..=255).step_by(17) {
            for g in (0..=255).step_by(17) {
                for b in (0..=255).step_by(17) {
                    let (h, s, v) = rgb_hsv([r, g, b], 0);
                    for (a, z) in hsv_rgb(h, s, v).iter().zip([r, g, b]) {
                        assert!((*a as i16 - z as i16).abs() <= 2);
                    }
                }
            }
        }
    }
    #[test]
    fn hex_validation() {
        assert_eq!(parse_hex("#00ff80"), Some([0, 255, 128]));
        assert!(parse_hex("#fffff").is_none());
        assert!(parse_hex("ééé").is_none());
    }
    #[test]
    fn native_precision() {
        assert_eq!(rgb_hsv([255, 0, 0], 0), (0, 1000, 1000));
        assert_ne!(hsv_rgb(0, 1000, 10), hsv_rgb(0, 1000, 20));
    }
}
