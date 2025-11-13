import {PropsWithChildren} from "react";
import {FluentProvider} from "@fluentui/react-components";
import {ThemeContext} from "./ThemeContext";
import {useThemeProvider} from "./useThemeProvider";
import {motion} from "framer-motion";
import styles from "./Theme.module.css";

export function ThemeProvider({children}: Readonly<PropsWithChildren>): JSX.Element {
    const themeContext = useThemeProvider();

    const FloatingPaths = ({position}: { position: number }) => {
        const paths = Array.from({length: 30}, (_, i) => ({
            id: i,
            d: `M-${380 - i * 5 * position} -${189 + i * 6}C-${
                380 - i * 5 * position
            } -${189 + i * 6} -${312 - i * 5 * position} ${216 - i * 6} ${
                152 - i * 5 * position
            } ${343 - i * 6}C${616 - i * 5 * position} ${470 - i * 6} ${
                684 - i * 5 * position
            } ${875 - i * 6} ${684 - i * 5 * position} ${875 - i * 6}`,
            color: `rgba(15,23,42,${0.1 + i * 0.03})`,
            width: 0.5 + i * 0.03,
        }));

        return (
            <div className={styles.floatingPaths01}>
                <svg className={styles.floatingPaths02} viewBox='0 0 696 316' fill='none'>
                    {paths.map((path) => (
                        <motion.path
                            key={path.id}
                            d={path.d}
                            stroke='currentColor'
                            strokeWidth={path.width}
                            strokeOpacity={0.1 + path.id * 0.03}
                            initial={{pathLength: 0.3, opacity: 0.6}}
                            animate={{
                                pathLength: 1,
                                opacity: [0.3, 0.6, 0.3],
                                pathOffset: [0, 1, 0],
                            }}
                            transition={{
                                duration: 20 + Math.random() * 10,
                                repeat: Number.POSITIVE_INFINITY,
                                ease: 'linear',
                            }}
                        />
                    ))}
                </svg>
            </div>
        );
    }

    return (
        <FluentProvider theme={themeContext.themeStyles}>
            <ThemeContext.Provider value={themeContext}>
                <div className={styles.floatingPaths}>
                    <FloatingPaths position={-1}/>
                    <FloatingPaths position={1}/>
                </div>
                <div className={styles.floatingPaths03}>
                    {children}
                </div>
            </ThemeContext.Provider>
        </FluentProvider>
    );
}
