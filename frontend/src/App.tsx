import { useState, useEffect } from 'react';
import axios from 'axios';
import { type Discussion, type Message, chargerDiscussions, sauvegarderDiscussions } from './utils/storage';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from 'recharts';

const Sparkline = ({ data, color }: { data: number[], color: string }) => (
  <ResponsiveContainer width="100%" height={40}>
    <LineChart data={data.map((v, i) => ({ i, v }))}>
      <Line type="monotone" dataKey="v" stroke={color} strokeWidth={2} dot={false} />
    </LineChart>
  </ResponsiveContainer>
);

function App() {
  const [discussions, setDiscussions] = useState<Discussion[]>([]);
  const [discussionActive, setDiscussionActive] = useState<string | null>(null);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [recherche, setRecherche] = useState('');
  const [menuOuvert, setMenuOuvert] = useState<string | null>(null);
  const [vues, setVues] = useState<{[key: string]: string}>({});
  const [kpis, setKpis] = useState<any>(null);

  const [langue, setLangue] = useState<'FR' | 'EN'>('FR');
  const [modeSombre, setModeSombre] = useState(false);

  useEffect(() => { 
    setDiscussions(chargerDiscussions()); 
    axios.get('http://localhost:8000/api/kpis').then(res => setKpis(res.data)).catch(() => {});
  }, []);

  useEffect(() => { if (discussions.length > 0) sauvegarderDiscussions(discussions); }, [discussions]);

  const T = {
    FR: { titre: "Assistant GenAI : monitoring post-trade", question: "Posez une question...", nouvelle: "+ Nouvelle conversation", recherche: "Rechercher...", attente: "Instructions en attente", echoue: "Instructions échouées", taux: "Taux de règlement (%)", avenir: "Règlements à venir", hier: "vs hier", jours: "7 prochains jours" },
    EN: { titre: "GenAI Assistant: post-trade monitoring", question: "Ask a question...", nouvelle: "+ New conversation", recherche: "Search...", attente: "Pending instructions", echoue: "Failed instructions", taux: "Settlement rate (%)", avenir: "Upcoming settlements", hier: "vs yesterday", jours: "Next 7 days" }
  };
  const t = T[langue];

  const COLORS = {
    bg: modeSombre ? '#111827' : '#f8fafc',
    card: modeSombre ? '#1f2937' : '#ffffff',
    text: modeSombre ? '#f3f4f6' : '#1e293b',
    textMuted: modeSombre ? '#9ca3af' : '#64748b',
    border: modeSombre ? '#374151' : '#e2e8f0',
    sidebar: '#0a192f',
    blue: '#0078d4',
    red: '#E8615B',
  };

  const demarrerMicro = () => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { alert("Navigateur non supporté."); return; }
    const recognition = new SR();
    recognition.lang = langue === 'FR' ? 'fr-FR' : 'en-US';
    recognition.onresult = (event: any) => setQuestion(event.results[0][0].transcript);
    recognition.start();
  };

  const poserQuestion = async (texteDirect?: string) => {
    const texte = texteDirect || question.trim();
    if (!texte) return;
    setQuestion(''); setLoading(true);
    const msgUser: Message = { id: Date.now().toString(), role: 'user', contenu: texte, timestamp: Date.now() };

    let currentDiscId = discussionActive;
    if (!currentDiscId) {
      const nouvelleDisc: Discussion = { id: Date.now().toString(), titre: texte.substring(0, 30), date: Date.now(), messages: [msgUser] };
      setDiscussions([nouvelleDisc, ...discussions]); setDiscussionActive(nouvelleDisc.id); currentDiscId = nouvelleDisc.id;
    } else {
      setDiscussions(discussions.map(d => d.id === currentDiscId ? { ...d, messages: [...d.messages, msgUser] } : d));
    }

    try {
      const res = await axios.post('http://localhost:8000/api/ask', { texte }, { timeout: 60000 });
      let contenuAssistant = res.data.type === 'info' || res.data.type === 'erreur' ? res.data.message : (res.data.type === 'rapport' ? "Rapport généré." : res.data.commentaire);
      const msgAssistant: Message = { id: (Date.now() + 1).toString(), role: 'assistant', contenu: contenuAssistant, timestamp: Date.now(), data: res.data };
      
      if (res.data.affichage) {
        setVues(prev => ({ ...prev, [msgAssistant.id]: res.data.affichage }));
      }

      setDiscussions(prev => prev.map(d => d.id === currentDiscId ? { ...d, messages: [...d.messages, msgAssistant] } : d));
    } catch (err: any) {
      let msg = "Une erreur est survenue.";
      if (err.code === 'ECONNABORTED') msg = "Le serveur a mis trop de temps à répondre. Réessayez.";
      else if (err.response) msg = `Erreur serveur (${err.response.status}).`;
      else if (err.request) msg = "Impossible de contacter le serveur. Docker est-il en marche ?";
      
      const msgErreur: Message = { id: (Date.now() + 1).toString(), role: 'assistant', contenu: msg, timestamp: Date.now() };
      setDiscussions(prev => prev.map(d => d.id === currentDiscId ? { ...d, messages: [...d.messages, msgErreur] } : d));
    }
    setLoading(false);
  };

  const supprimerDiscussion = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDiscussions(discussions.filter(d => d.id !== id));
    if (discussionActive === id) setDiscussionActive(null);
    setMenuOuvert(null);
  };

  const renommerDiscussion = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const nouveauTitre = prompt("Nouveau titre :");
    if (nouveauTitre) {
      setDiscussions(discussions.map(d => d.id === id ? { ...d, titre: nouveauTitre } : d));
    }
    setMenuOuvert(null);
  };

  const grouperMenus = (discs: Discussion[]) => {
    const aujourdhui = new Date().toISOString().split('T')[0];
    const hier = new Date(Date.now() - 86400000).toISOString().split('T')[0];
    const ilYa7Jours = new Date(Date.now() - 7 * 86400000).toISOString().split('T')[0];
    const ilYa30Jours = new Date(Date.now() - 30 * 86400000).toISOString().split('T')[0];
    const groupes: { [key: string]: Discussion[] } = { "AUJOURD'HUI": [], "HIER": [], "7 DERNIERS JOURS": [], "30 DERNIERS JOURS": [], "PLUS ANCIEN": [] };
    discs.forEach(d => {
      const dateStr = new Date(d.date).toISOString().split('T')[0];
      if (dateStr === aujourdhui) groupes["AUJOURD'HUI"].push(d);
      else if (dateStr === hier) groupes["HIER"].push(d);
      else if (dateStr > ilYa7Jours) groupes["7 DERNIERS JOURS"].push(d);
      else if (dateStr > ilYa30Jours) groupes["30 DERNIERS JOURS"].push(d);
      else groupes["PLUS ANCIEN"].push(d);
    });
    return groupes;
  };

  const groupes = grouperMenus(discussions.filter(d => d.titre.toLowerCase().includes(recherche.toLowerCase())));
  const discussionCourante = discussions.find(d => d.id === discussionActive);

  return (
    <div style={{ display: 'flex', width: '100vw', height: '100vh', backgroundColor: COLORS.bg, fontFamily: "'Segoe UI', sans-serif", color: COLORS.text, transition: 'all 0.3s' }}>
      
      {/* SIDEBAR */}
      <div style={{ width: '280px', backgroundColor: COLORS.sidebar, display: 'flex', flexDirection: 'column', color: '#e2e8f0' }}>
        
        <div style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <img src="/logo.png" alt="Vermeg" style={{ height: '32px', width: 'auto' }} onError={(e) => { e.currentTarget.style.display = 'none'; }} />
          <span style={{ fontSize: '18px', fontWeight: 700 }}>Vermeg</span>
        </div>

        <div style={{ padding: '0 20px 20px 20px', display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
          <button onClick={() => setDiscussionActive(null)} style={{ width: '100%', padding: '12px', backgroundColor: COLORS.blue, color: '#ffffff', border: 'none', borderRadius: '6px', fontWeight: 600, cursor: 'pointer', marginBottom: '20px' }}>
            {t.nouvelle}
          </button>
          
          <div style={{ marginBottom: '20px' }}>
            <input type="text" placeholder={t.recherche} value={recherche} onChange={(e) => setRecherche(e.target.value)} style={{ width: '100%', padding: '10px', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#ffffff', outline: 'none', fontSize: '13px' }} />
          </div>

          <div style={{ flex: 1, overflowY: 'auto' }}>
            {Object.entries(groupes).map(([nomGroupe, liste]) => {
              if (liste.length === 0) return null;
              return (
                <div key={nomGroupe} style={{ marginBottom: '15px' }}>
                  <div style={{ fontSize: '11px', color: '#8892b0', textTransform: 'uppercase', marginBottom: '8px', fontWeight: 600 }}>{nomGroupe}</div>
                  {liste.map((d) => (
                    <div key={d.id} onClick={() => setDiscussionActive(d.id)} style={{ padding: '10px 12px', marginBottom: '4px', backgroundColor: discussionActive === d.id ? '#1e293b' : 'transparent', borderRadius: '6px', fontSize: '13px', cursor: 'pointer', color: discussionActive === d.id ? '#ffffff' : '#a8b2d1', display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.titre}</span>
                      <div style={{ position: 'relative' }}>
                        <button onClick={(e) => { e.stopPropagation(); setMenuOuvert(menuOuvert === d.id ? null : d.id); }} style={{ background: 'transparent', border: 'none', color: '#a8b2d1', cursor: 'pointer', fontSize: '16px' }}>⋮</button>
                        {menuOuvert === d.id && (
                          <div style={{ position: 'absolute', right: 0, top: '100%', backgroundColor: COLORS.card, borderRadius: '6px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', zIndex: 10, width: '140px', display: 'flex', flexDirection: 'column' }}>
                            <button onClick={(e) => renommerDiscussion(d.id, e)} style={{ padding: '10px', textAlign: 'left', background: 'none', border: 'none', cursor: 'pointer', color: COLORS.text, fontSize: '13px' }}>Renommer</button>
                            <button onClick={(e) => supprimerDiscussion(d.id, e)} style={{ padding: '10px', textAlign: 'left', background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444', fontSize: '13px' }}>Supprimer</button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* CONTENU PRINCIPAL */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        
        {/* Header */}
        <div style={{ padding: '20px 40px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1 style={{ fontSize: '26px', margin: 0, fontWeight: 700, color: modeSombre ? '#ffffff' : COLORS.sidebar }}>{t.titre}</h1>
            <p style={{ margin: '5px 0 0 0', color: COLORS.textMuted, fontSize: '13px' }}>Mis à jour à {new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</p>
          </div>
          
          <div style={{ display: 'flex', gap: '8px' }}>
            <button onClick={() => setLangue('FR')} style={{ padding: '8px 14px', backgroundColor: langue === 'FR' ? COLORS.blue : COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: '8px', cursor: 'pointer', fontWeight: 600, color: langue === 'FR' ? '#ffffff' : COLORS.text }}>FR</button>
            <button onClick={() => setLangue('EN')} style={{ padding: '8px 14px', backgroundColor: langue === 'EN' ? COLORS.blue : COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: '8px', cursor: 'pointer', fontWeight: 600, color: langue === 'EN' ? '#ffffff' : COLORS.text }}>EN</button>
            <button onClick={() => setModeSombre(!modeSombre)} style={{ padding: '8px 14px', backgroundColor: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: '8px', cursor: 'pointer', color: COLORS.text }}>
              {modeSombre ? '☀' : '☾'}
            </button>
            <button onClick={() => window.location.reload()} style={{ padding: '8px 14px', backgroundColor: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: '8px', cursor: 'pointer', color: COLORS.text }}>↻</button>
          </div>
        </div>

        {/* Cartes KPI */}
        <div style={{ padding: '0 40px', display: 'flex', gap: '20px', marginBottom: '30px' }}>
          
          <div style={{ flex: 1, backgroundColor: COLORS.card, padding: '20px', borderRadius: '12px', border: `1px solid ${COLORS.border}` }}>
            <div style={{ fontSize: '13px', color: COLORS.textMuted, marginBottom: '8px' }}>{t.attente}</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
              <div style={{ fontSize: '32px', fontWeight: 'bold', color: modeSombre ? '#ffffff' : COLORS.sidebar }}>{kpis?.attente || '-'}</div>
              <div style={{ width: '60px' }}><Sparkline data={kpis?.spark_attente || []} color="#f59e0b" /></div>
            </div>
            <div style={{ fontSize: '11px', color: kpis?.attente_tendance >= 0 ? '#f59e0b' : '#10b981', marginTop: '8px', fontWeight: 600 }}>
              {kpis?.attente_tendance >= 0 ? '▲' : '▼'} {Math.abs(kpis?.attente_tendance || 0)} {t.hier}
            </div>
          </div>

          <div style={{ flex: 1, backgroundColor: COLORS.card, padding: '20px', borderRadius: '12px', border: `1px solid ${COLORS.border}` }}>
            <div style={{ fontSize: '13px', color: COLORS.textMuted, marginBottom: '8px' }}>{t.echoue}</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
              <div style={{ fontSize: '32px', fontWeight: 'bold', color: COLORS.red }}>{kpis?.echoue || '-'}</div>
              <div style={{ width: '60px' }}><Sparkline data={kpis?.spark_echoue || []} color={COLORS.red} /></div>
            </div>
            <div style={{ fontSize: '11px', color: kpis?.echoue_tendance <= 0 ? '#10b981' : COLORS.red, marginTop: '8px', fontWeight: 600 }}>
              {kpis?.echoue_tendance <= 0 ? '▼' : '▲'} {Math.abs(kpis?.echoue_tendance || 0)} {t.hier}
            </div>
          </div>

          <div style={{ flex: 1, backgroundColor: COLORS.card, padding: '20px', borderRadius: '12px', border: `1px solid ${COLORS.border}` }}>
            <div style={{ fontSize: '13px', color: COLORS.textMuted, marginBottom: '8px' }}>{t.taux}</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
              <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#10b981' }}>{kpis?.taux || '-'}</div>
              <div style={{ width: '60px' }}><Sparkline data={kpis?.spark_taux || []} color="#10b981" /></div>
            </div>
            <div style={{ fontSize: '11px', color: kpis?.taux_tendance >= 0 ? '#10b981' : COLORS.red, marginTop: '8px', fontWeight: 600 }}>
              {kpis?.taux_tendance >= 0 ? '▲' : '▼'} {Math.abs(kpis?.taux_tendance || 0)} pts {t.hier}
            </div>
          </div>

          <div style={{ flex: 1, backgroundColor: COLORS.card, padding: '20px', borderRadius: '12px', border: `1px solid ${COLORS.border}` }}>
            <div style={{ fontSize: '13px', color: COLORS.textMuted, marginBottom: '8px' }}>{t.avenir}</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
              <div style={{ fontSize: '32px', fontWeight: 'bold', color: modeSombre ? '#ffffff' : COLORS.sidebar }}>{kpis?.a_venir || '-'}</div>
            </div>
            <div style={{ fontSize: '11px', color: COLORS.textMuted, marginTop: '8px', fontWeight: 600 }}>{t.jours}</div>
          </div>

        </div>

        {/* Chat */}
        <div style={{ flex: 1, padding: '0 40px', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          {!discussionCourante && !loading && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: COLORS.textMuted }}>
              <h2 style={{ fontWeight: 400, fontSize: '18px' }}>Posez une question sur vos données post-trade.</h2>
            </div>
          )}

          {discussionCourante && (
            <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '20px', paddingBottom: '20px' }}>
              {discussionCourante.messages.map((msg: Message, index: number) => {
                if (msg.role === 'user') {
                  return (
                    <div key={index} style={{ alignSelf: 'flex-end', maxWidth: '70%' }}>
                      <div style={{ backgroundColor: COLORS.blue, padding: '12px 20px', borderRadius: '20px 20px 4px 20px', color: '#ffffff', fontSize: '14px' }}>{msg.contenu}</div>
                    </div>
                  );
                }
                const data = msg.data;
                const vueActive = vues[msg.id] || data?.affichage || 'tableau';
                return (
                  <div key={index} style={{ alignSelf: 'flex-start', width: '100%' }}>
                    <div style={{ display: 'flex', gap: '15px' }}>
                      <div style={{ width: '32px', height: '32px', backgroundColor: COLORS.sidebar, borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 'bold', fontSize: '12px' }}>AI</div>
                      <div style={{ flex: 1 }}>
                        <p style={{ lineHeight: '1.6', margin: '0 0 15px 0', fontSize: '15px' }}>{msg.contenu}</p>
                        
                        {data?.type === 'sql' && data.resultat && data.resultat.length > 0 && (
                          <>
                            {data.resultat.length === 1 && (
                              <div style={{ display: 'flex', gap: '20px', marginBottom: '15px' }}>
                                {data.colonnes.map((col: string) => (
                                  <div key={col} style={{ flex: 1, backgroundColor: modeSombre ? '#2d3748' : '#f8fafc', padding: '20px', borderRadius: '8px', border: `1px solid ${COLORS.border}` }}>
                                    <div style={{ fontSize: '12px', color: COLORS.textMuted, textTransform: 'uppercase', marginBottom: '8px' }}>{col.replace('_', ' ')}</div>
                                    <div style={{ fontSize: '32px', fontWeight: 'bold', color: modeSombre ? '#ffffff' : COLORS.sidebar }}>{data.resultat[0][col]}</div>
                                  </div>
                                ))}
                              </div>
                            )}

                            {data.resultat.length > 1 && (
                              <>
                                <div style={{ display: 'flex', gap: '15px', marginBottom: '15px', alignItems: 'center' }}>
                                  <span style={{ fontSize: '13px', color: COLORS.textMuted, fontWeight: 600 }}>Affichage :</span>
                                  {['tableau', 'histogramme', 'courbe', 'kpi'].map((v) => (
                                    <label key={v} style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '13px', cursor: 'pointer', color: vueActive === v ? COLORS.text : COLORS.textMuted }}>
                                      <input type="radio" name={`vue_${msg.id}`} checked={vueActive === v} onChange={() => setVues(prev => ({ ...prev, [msg.id]: v }))} style={{ accentColor: COLORS.blue }} />
                                      {v.charAt(0).toUpperCase() + v.slice(1)}
                                    </label>
                                  ))}
                                </div>

                                {vueActive === 'kpi' && data.resultat.length > 1 && (
                                  <div style={{ padding: '20px', backgroundColor: COLORS.card, borderRadius: '8px', border: `1px solid ${COLORS.border}`, marginBottom: '15px' }}>
                                    <p style={{ margin: 0, fontSize: '16px', fontWeight: 'bold', color: COLORS.sidebar }}>
                                      Nombre total de lignes : {data.resultat.length}
                                    </p>
                                    <p style={{ margin: '5px 0 0 0', fontSize: '13px', color: COLORS.textMuted }}>
                                      (Sélectionnez "Tableau" pour voir les détails)
                                    </p>
                                  </div>
                                )}

                                {vueActive === 'histogramme' && data.colonnes.length >= 2 && (
                                  <div style={{ width: '100%', height: 350, marginBottom: '15px' }}>
                                    <ResponsiveContainer width="100%" height="100%">
                                      <BarChart data={data.resultat}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={COLORS.border} />
                                        <XAxis dataKey={data.colonnes[0]} tick={{ fontSize: 12, fill: COLORS.textMuted }} />
                                        <YAxis tick={{ fontSize: 12, fill: COLORS.textMuted }} />
                                        <Tooltip contentStyle={{ backgroundColor: COLORS.card, border: `1px solid ${COLORS.border}`, color: COLORS.text }} />
                                        <Bar dataKey={data.colonnes[1]} fill={COLORS.blue} radius={[4, 4, 0, 0]} />
                                      </BarChart>
                                    </ResponsiveContainer>
                                  </div>
                                )}

                                {vueActive === 'courbe' && data.colonnes.length >= 2 && (
                                  <div style={{ width: '100%', height: 350, marginBottom: '15px' }}>
                                    <ResponsiveContainer width="100%" height="100%">
                                      <LineChart data={data.resultat}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={COLORS.border} />
                                        <XAxis dataKey={data.colonnes[0]} tick={{ fontSize: 12, fill: COLORS.textMuted }} />
                                        <YAxis tick={{ fontSize: 12, fill: COLORS.textMuted }} />
                                        <Tooltip contentStyle={{ backgroundColor: COLORS.card, border: `1px solid ${COLORS.border}`, color: COLORS.text }} />
                                        <Line type="monotone" dataKey={data.colonnes[1]} stroke={COLORS.blue} strokeWidth={2} dot={{ r: 4 }} />
                                      </LineChart>
                                    </ResponsiveContainer>
                                  </div>
                                )}

                                {vueActive === 'tableau' && (
                                  <div style={{ border: `1px solid ${COLORS.border}`, borderRadius: '8px', overflowX: 'auto', marginBottom: '15px', width: '100%' }}>
                                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                                      <thead style={{ backgroundColor: modeSombre ? '#2d3748' : '#f8fafc', borderBottom: `1px solid ${COLORS.border}` }}>
                                        <tr>{data.colonnes.map((col: string) => <th key={col} style={{ padding: '12px 16px', textAlign: 'left', color: COLORS.textMuted, fontWeight: 600 }}>{col}</th>)}</tr>
                                      </thead>
                                      <tbody>
                                        {data.resultat.map((ligne: any, i: number) => (
                                          <tr key={i} style={{ borderBottom: `1px solid ${COLORS.border}` }}>
                                            {data.colonnes.map((col: string) => <td key={col} style={{ padding: '12px 16px' }}>{ligne[col]}</td>)}
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  </div>
                                )}
                              </>
                            )}

                            <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
                              <a href="http://localhost:8000/api/download/excel" target="_blank" style={{ padding: '8px 16px', backgroundColor: '#10b981', color: 'white', textDecoration: 'none', borderRadius: '20px', fontSize: '13px', fontWeight: 600 }}>Excel</a>
                              <a href="http://localhost:8000/api/download/csv" target="_blank" style={{ padding: '8px 16px', backgroundColor: COLORS.blue, color: 'white', textDecoration: 'none', borderRadius: '20px', fontSize: '13px', fontWeight: 600 }}>CSV</a>
                            </div>
                          </>
                        )}

                        {data?.type === 'rapport' && (
                          <div style={{ marginTop: '10px', padding: '20px', backgroundColor: modeSombre ? '#1e293b' : '#f0f9ff', borderRadius: '8px', border: `1px solid ${COLORS.border}` }}>
                            <h3 style={{ margin: '0 0 15px 0', fontSize: '18px', fontWeight: 600, color: modeSombre ? '#ffffff' : '#0c4a6e' }}>{data.titre}</h3>
                            
                            <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: COLORS.card, borderRadius: '8px', border: `1px solid ${COLORS.border}` }}>
                              <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', color: modeSombre ? '#ffffff' : '#0c4a6e' }}>Synthèse</h4>
                              <p style={{ margin: 0, fontSize: '14px', color: COLORS.textMuted, lineHeight: '1.6' }}>{data.synthese || "Rapport généré."}</p>
                            </div>

                            {data.indicateurs && data.indicateurs.length > 0 && (
                              <div style={{ display: 'flex', gap: '15px', marginBottom: '20px' }}>
                                {data.indicateurs.map((ind: any, i: number) => (
                                  <div key={i} style={{ flex: 1, backgroundColor: COLORS.card, padding: '15px', borderRadius: '8px', border: `1px solid ${COLORS.border}` }}>
                                    <div style={{ fontSize: '12px', color: COLORS.textMuted, marginBottom: '5px' }}>{ind[0]}</div>
                                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: modeSombre ? '#ffffff' : '#0c4a6e' }}>{ind[1]}</div>
                                  </div>
                                ))}
                              </div>
                            )}

                            {data.sections && data.sections.length > 0 && (
                              <div style={{ marginBottom: '20px' }}>
                                {data.sections.map((section: any, idx: number) => (
                                  <div key={idx} style={{ marginBottom: '25px' }}>
                                    <h4 style={{ margin: '0 0 10px 0', fontSize: '15px', color: modeSombre ? '#ffffff' : '#0c4a6e', fontWeight: 600 }}>{section.titre}</h4>
                                    
                                    {(section.affichage === 'histogramme' || section.affichage === 'courbe') && section.colonnes.length >= 2 && (
                                      <div style={{ width: '100%', height: 300, backgroundColor: COLORS.card, borderRadius: '8px', padding: '15px', border: `1px solid ${COLORS.border}` }}>
                                        <ResponsiveContainer width="100%" height="100%">
                                          {section.affichage === 'histogramme' ? (
                                            <BarChart data={section.resultat}>
                                              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={COLORS.border} />
                                              <XAxis dataKey={section.colonnes[0]} tick={{ fontSize: 11, fill: COLORS.textMuted }} />
                                              <YAxis tick={{ fontSize: 11, fill: COLORS.textMuted }} />
                                              <Tooltip contentStyle={{ backgroundColor: COLORS.card, border: `1px solid ${COLORS.border}`, color: COLORS.text }} />
                                              <Bar dataKey={section.colonnes[1]} fill={COLORS.blue} radius={[4, 4, 0, 0]} />
                                            </BarChart>
                                          ) : (
                                            <LineChart data={section.resultat}>
                                              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={COLORS.border} />
                                              <XAxis dataKey={section.colonnes[0]} tick={{ fontSize: 11, fill: COLORS.textMuted }} />
                                              <YAxis tick={{ fontSize: 11, fill: COLORS.textMuted }} />
                                              <Tooltip contentStyle={{ backgroundColor: COLORS.card, border: `1px solid ${COLORS.border}`, color: COLORS.text }} />
                                              <Line type="monotone" dataKey={section.colonnes[1]} stroke={COLORS.blue} strokeWidth={2} dot={{ r: 3 }} />
                                            </LineChart>
                                          )}
                                        </ResponsiveContainer>
                                      </div>
                                    )}

                                    {section.affichage === 'tableau' && (
                                      <div style={{ border: `1px solid ${COLORS.border}`, borderRadius: '8px', overflowX: 'auto', backgroundColor: COLORS.card }}>
                                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                                          <thead style={{ backgroundColor: modeSombre ? '#2d3748' : '#f8fafc', borderBottom: `1px solid ${COLORS.border}` }}>
                                            <tr>{section.colonnes.map((col: string) => <th key={col} style={{ padding: '10px 15px', textAlign: 'left', color: COLORS.textMuted, fontWeight: 600 }}>{col}</th>)}</tr>
                                          </thead>
                                          <tbody>
                                            {section.resultat.slice(0, 10).map((ligne: any, i: number) => (
                                              <tr key={i} style={{ borderBottom: `1px solid ${COLORS.border}` }}>
                                                {section.colonnes.map((col: string) => <td key={col} style={{ padding: '10px 15px' }}>{ligne[col]}</td>)}
                                              </tr>
                                            ))}
                                          </tbody>
                                        </table>
                                        {section.resultat.length > 10 && (
                                          <div style={{ padding: '10px', textAlign: 'center', fontSize: '12px', color: COLORS.textMuted }}>
                                            ... {section.resultat.length - 10} lignes supplémentaires (voir PDF ou Excel)
                                          </div>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}

                            <div style={{ display: 'flex', gap: '10px', marginTop: '20px', paddingTop: '15px', borderTop: `1px solid ${COLORS.border}` }}>
                              <a href="http://localhost:8000/api/download/pdf" target="_blank" style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', backgroundColor: COLORS.card, border: `1px solid ${COLORS.border}`, textDecoration: 'none', borderRadius: '20px', fontSize: '13px', fontWeight: 600, color: COLORS.text }}>
                                <span style={{ color: COLORS.red, fontSize: '16px' }}>↓</span> PDF
                              </a>
                              <a href="http://localhost:8000/api/download/excel" target="_blank" style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', backgroundColor: COLORS.card, border: `1px solid ${COLORS.border}`, textDecoration: 'none', borderRadius: '20px', fontSize: '13px', fontWeight: 600, color: COLORS.text }}>
                                <span style={{ color: '#10b981', fontSize: '16px' }}>↓</span> Excel
                              </a>
                              <a href="http://localhost:8000/api/download/csv" target="_blank" style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', backgroundColor: COLORS.card, border: `1px solid ${COLORS.border}`, textDecoration: 'none', borderRadius: '20px', fontSize: '13px', fontWeight: 600, color: COLORS.text }}>
                                <span style={{ color: COLORS.blue, fontSize: '16px' }}>↓</span> CSV
                              </a>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {loading && (
            <div style={{ alignSelf: 'flex-start', display: 'flex', gap: '15px', padding: '10px 0' }}>
              <div style={{ width: '32px', height: '32px', backgroundColor: COLORS.sidebar, borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 'bold', fontSize: '12px' }}>AI</div>
              <div style={{ display: 'flex', alignItems: 'center', color: COLORS.textMuted, fontSize: '14px' }}>Analyse en cours...</div>
            </div>
          )}
        </div>

        {/* Barre de saisie */}
        <div style={{ padding: '20px 40px' }}>
          <div style={{ maxWidth: '850px', margin: '0 auto', position: 'relative' }}>
            <input 
              type="text" 
              value={question} 
              onChange={(e) => setQuestion(e.target.value)} 
              onKeyDown={(e) => e.key === 'Enter' && poserQuestion()} 
              placeholder={t.question} 
              style={{ width: '100%', padding: '16px 100px 16px 20px', backgroundColor: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: '12px', fontSize: '14px', color: COLORS.text, outline: 'none' }} 
            />
            <button onClick={demarrerMicro} style={{ position: 'absolute', right: '55px', top: '8px', bottom: '8px', width: '40px', backgroundColor: 'transparent', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={COLORS.textMuted} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                <line x1="12" y1="19" x2="12" y2="23"></line>
                <line x1="8" y1="23" x2="16" y2="23"></line>
              </svg>
            </button>
            <button onClick={() => poserQuestion()} style={{ position: 'absolute', right: '8px', top: '8px', bottom: '8px', width: '40px', backgroundColor: COLORS.blue, color: 'white', border: 'none', borderRadius: '8px', cursor: question ? 'pointer' : 'default' }}>↑</button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;